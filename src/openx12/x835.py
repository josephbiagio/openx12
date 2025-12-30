"""
835 ERA (Electronic Remittance Advice) Parser

Parse X12 835 files into structured data with multiple output formats.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime


def parse(content: str) -> "ERA":
    """Parse 835 ERA content and return parser object."""
    return ERA(content)


BILL_TO_HINT_PRIMARY = "primary"
BILL_TO_HINT_SECONDARY = "secondary"
BILL_TO_HINT_TERTIARY = "tertiary"
BILL_TO_HINT_PATIENT = "patient"

CLAIM_STATUS_TO_BILL_TO = {
    "1": BILL_TO_HINT_SECONDARY,
    "2": BILL_TO_HINT_TERTIARY,
    "3": BILL_TO_HINT_PATIENT,
}


class ERA:
    """
    Parse and access X12 835 ERA (Electronic Remittance Advice) data.

    Usage:
        era = ERA(edi_content)
        era.summary()    # Quick overview
        era.json()       # Full structured data
        era.table()      # Display-friendly tables

        # Direct access
        era.payer
        era.payee
        era.claims
        era.payment_amount
    """

    def __init__(self, content: str):
        self.content = content.strip().replace("\n", "").replace("\r", "")
        self._segments = self._split_segments()
        self._parsed: Optional[Dict[str, Any]] = None
        self._parse()

    def _split_segments(self) -> List[str]:
        return [seg.strip() for seg in self.content.split("~") if seg.strip()]

    def _parse_segment(self, segment: str) -> Dict[str, Any]:
        parts = segment.split("*")
        return {
            "segment_id": parts[0] if parts else "",
            "elements": parts[1:] if len(parts) > 1 else [],
            "raw": segment,
        }

    def _parse(self) -> None:
        """Parse all segments into structured data."""
        result: Dict[str, Any] = {
            "file_type": "835",
            "parsed_at": datetime.now().isoformat(),
            "segments": [],
            "summary": {
                "total_segments": len(self._segments),
                "claims": [],
                "payments": {},
            },
        }

        current_claim: Optional[Dict[str, Any]] = None
        current_service: Optional[Dict[str, Any]] = None

        for raw in self._segments:
            seg = self._parse_segment(raw)
            seg_id = seg["segment_id"]
            els = seg["elements"]
            result["segments"].append(seg)

            if seg_id == "ISA":
                result["interchange"] = {
                    "sender_id": els[5] if len(els) > 5 else "",
                    "receiver_id": els[7] if len(els) > 7 else "",
                    "date": els[8] if len(els) > 8 else "",
                    "time": els[9] if len(els) > 9 else "",
                }
            elif seg_id == "GS":
                result["group"] = {
                    "sender_code": els[1] if len(els) > 1 else "",
                    "receiver_code": els[2] if len(els) > 2 else "",
                    "date": els[3] if len(els) > 3 else "",
                    "time": els[4] if len(els) > 4 else "",
                }
            elif seg_id == "BPR":
                result["summary"]["payments"] = {
                    "amount": _safe_float(els[1]) if len(els) > 1 else 0.0,
                    "method": els[0] if len(els) > 0 else "",
                }
            elif seg_id == "TRN":
                result.setdefault("payment_trace", {})
                result["payment_trace"].update({
                    "trace_type": els[0] if len(els) > 0 else "",
                    "trace_number": els[1] if len(els) > 1 else "",
                })
            elif seg_id == "N1":
                entity_id = els[0] if len(els) > 0 else ""
                entity_name = els[1] if len(els) > 1 else ""
                id_qualifier = els[2] if len(els) > 2 else ""
                id_code = els[3] if len(els) > 3 else ""
                if entity_id == "PR":
                    result.setdefault("payer", {})
                    result["payer"]["name"] = entity_name
                    result["payer"]["id_qualifier"] = id_qualifier
                    result["payer"]["id"] = id_code
                elif entity_id == "PE":
                    result.setdefault("payee", {})
                    result["payee"]["name"] = entity_name
                    result["payee"]["id_qualifier"] = id_qualifier
                    result["payee"]["id"] = id_code
            elif seg_id == "REF" and current_claim is None and current_service is None:
                ref_qual = els[0] if len(els) > 0 else ""
                ref_val = els[1] if len(els) > 1 else ""
                if ref_qual == "2U":
                    result.setdefault("payer", {})
                    result["payer"]["id"] = ref_val
                elif ref_qual == "EV":
                    result.setdefault("payee", {})
                    result["payee"]["reference_id"] = ref_val
            elif seg_id == "CLP":
                current_claim = {
                    "patient_control_number": els[0] if len(els) > 0 else "",
                    "claim_status": els[1] if len(els) > 1 else "",
                    "total_claim_charge": _safe_float(els[2]) if len(els) > 2 else 0.0,
                    "claim_payment_amount": _safe_float(els[3]) if len(els) > 3 else 0.0,
                    "patient_responsibility": 0.0,
                    "payer_claim_control_number": els[6] if len(els) > 6 else "",
                    "claim_filing_indicator_code": els[5] if len(els) > 5 else "",
                    "provider_adjustments": 0.0,
                    "other_adjustments": 0.0,
                    "services": [],
                }
                result["summary"]["claims"].append(current_claim)
                current_service = None
            elif seg_id == "SVC" and current_claim is not None:
                procedure = els[0] if len(els) > 0 else ""
                cpt = ""
                modifiers: List[str] = []
                if ":" in procedure:
                    parts = procedure.split(":")
                    if len(parts) > 1:
                        cpt = parts[1]
                    if len(parts) > 2:
                        modifiers = parts[2:]
                current_service = {
                    "cpt_code": cpt,
                    "modifiers": modifiers,
                    "line_item_charge_amount": _safe_float(els[1]) if len(els) > 1 else 0.0,
                    "line_item_payment_amount": _safe_float(els[2]) if len(els) > 2 else 0.0,
                    "patient_responsibility": 0.0,
                    "line_item_control_number": "",
                    "adjustments": [],
                }
                current_claim["services"].append(current_service)
            elif seg_id == "REF" and current_service is not None:
                if len(els) >= 2 and els[0] == "6R":
                    current_service["line_item_control_number"] = els[1]
            elif seg_id == "CAS":
                group_code = els[0] if len(els) > 0 else ""
                adjustments = _parse_cas_adjustments(els[1:])
                target = current_service if current_service is not None else current_claim
                if target is not None:
                    target.setdefault("adjustments", [])
                    for adj in adjustments:
                        target["adjustments"].append({"group": group_code, **adj})
                        if group_code == "PR":
                            target["patient_responsibility"] = float(target.get("patient_responsibility", 0.0)) + adj["amount"]
                        elif group_code == "CO":
                            target_key = "provider_adjustments" if target is current_claim else "provider_adjustment_line"
                            target[target_key] = float(target.get(target_key, 0.0)) + adj["amount"]
                        elif group_code == "OA":
                            target_key = "other_adjustments" if target is current_claim else "other_adjustment_line"
                            target[target_key] = float(target.get(target_key, 0.0)) + adj["amount"]
            elif seg_id == "AMT":
                amt_qual = els[0] if len(els) > 0 else ""
                amt_val = _safe_float(els[1]) if len(els) > 1 else 0.0
                target = current_service if current_service is not None else current_claim
                if target is not None:
                    target.setdefault("amounts", {})
                    target["amounts"][amt_qual] = amt_val
                    if amt_qual == "B6":
                        target["allowed_amount"] = amt_val
                    elif amt_qual == "AU":
                        target["coverage_amount"] = amt_val
                    elif amt_qual == "DY":
                        target["per_day_limit"] = amt_val
                    elif amt_qual == "F5":
                        target["patient_paid_amount"] = amt_val
                    elif amt_qual == "I":
                        target["interest_amount"] = amt_val
                    elif amt_qual == "T":
                        target["tax_amount"] = amt_val
            elif seg_id == "DTM":
                qualifier = els[0] if len(els) > 0 else ""
                date_val = els[2] if len(els) > 2 else None
                if date_val and len(date_val) == 8:
                    try:
                        yyyy, mm, dd = int(date_val[0:4]), int(date_val[4:6]), int(date_val[6:8])
                        if current_service is not None and qualifier == "472":
                            current_service["service_date"] = f"{yyyy:04d}-{mm:02d}-{dd:02d}"
                        elif current_claim is not None and qualifier in ("232", "233", "434", "435", "050", "2320"):
                            key = "claim_date_from" if qualifier in ("232", "434", "050") else "claim_date_to"
                            current_claim[key] = f"{yyyy:04d}-{mm:02d}-{dd:02d}"
                    except Exception:
                        pass
            elif seg_id == "PLB":
                result.setdefault("plb", []).append({"raw": seg["raw"]})

        # Finalize claim-level aggregates and derive bill-to hints
        for claim in result["summary"]["claims"]:
            service_pr_total = sum(
                _safe_float(service.get("patient_responsibility"))
                for service in claim.get("services", [])
            )
            claim["patient_responsibility"] = _safe_float(claim.get("patient_responsibility")) + service_pr_total
            claim["bill_to_hint"] = _derive_bill_to_hint(
                claim.get("claim_status"),
                claim.get("patient_responsibility"),
            )

        self._parsed = result

    # -------------------------------------------------------------------------
    # Public Properties
    # -------------------------------------------------------------------------

    @property
    def payer(self) -> Dict[str, Any]:
        """Payer information (name, ID)."""
        return self._parsed.get("payer", {})

    @property
    def payee(self) -> Dict[str, Any]:
        """Payee/provider information (name, ID)."""
        return self._parsed.get("payee", {})

    @property
    def claims(self) -> List[Dict[str, Any]]:
        """List of all claims in this remittance."""
        return self._parsed.get("summary", {}).get("claims", [])

    @property
    def payment_amount(self) -> float:
        """Total payment amount."""
        return self._parsed.get("summary", {}).get("payments", {}).get("amount", 0.0)

    @property
    def check_number(self) -> str:
        """Check/trace number."""
        return self._parsed.get("payment_trace", {}).get("trace_number", "")

    @property
    def payment_method(self) -> str:
        """Payment method code."""
        return self._parsed.get("summary", {}).get("payments", {}).get("method", "")

    # -------------------------------------------------------------------------
    # Output Methods
    # -------------------------------------------------------------------------

    def json(self) -> Dict[str, Any]:
        """Return full parsed data as structured dictionary."""
        return self._parsed

    def summary(self) -> Dict[str, Any]:
        """Return concise summary with key information."""
        claims = self.claims
        total_charged = sum(c.get("total_claim_charge", 0) for c in claims)
        total_paid = sum(c.get("claim_payment_amount", 0) for c in claims)
        total_patient_resp = sum(c.get("patient_responsibility", 0) for c in claims)

        return {
            "file_type": "835 (ERA/Remittance)",
            "payer": self.payer.get("name", ""),
            "payer_id": self.payer.get("id", ""),
            "payee": self.payee.get("name", ""),
            "payee_id": self.payee.get("id", ""),
            "check_number": self.check_number,
            "payment_amount": self.payment_amount,
            "payment_method": self.payment_method,
            "payment_date": self._parsed.get("interchange", {}).get("date", ""),
            "total_claims": len(claims),
            "total_charged": total_charged,
            "total_paid": total_paid,
            "total_adjustments": total_charged - total_paid,
            "total_patient_responsibility": total_patient_resp,
        }

    def table(self) -> str:
        """Return display-friendly formatted text table."""
        lines: List[str] = []

        # File info header
        lines.append("=" * 80)
        lines.append("835 ERA (Electronic Remittance Advice)")
        lines.append("=" * 80)
        lines.append(f"Payer:    {self.payer.get('name', 'N/A')}")
        lines.append(f"Payee:    {self.payee.get('name', 'N/A')}")
        lines.append(f"Payment:  ${self.payment_amount:.2f} ({self.payment_method})")
        lines.append(f"Check #:  {self.check_number}")
        lines.append("")

        # Claims table
        claims_data = []
        for claim in self.claims:
            claims_data.append({
                "Claim #": claim.get("patient_control_number", ""),
                "Status": claim.get("claim_status", ""),
                "Charge": f"${claim.get('total_claim_charge', 0.0):.2f}",
                "Paid": f"${claim.get('claim_payment_amount', 0.0):.2f}",
                "Allowed": f"${claim.get('allowed_amount', 0.0):.2f}",
                "PR": f"${claim.get('patient_responsibility', 0.0):.2f}",
                "Bill To": claim.get("bill_to_hint", BILL_TO_HINT_PRIMARY),
            })

        if claims_data:
            lines.append("CLAIMS")
            lines.append("-" * 80)
            lines.append(_format_text_table(claims_data))
            lines.append("")

        # Services table
        services_data = []
        for claim in self.claims:
            for idx, svc in enumerate(claim.get("services", [])):
                pr_amt = float(svc.get("patient_responsibility", 0.0))
                allowed_amt = float(svc.get("allowed_amount", 0.0))
                services_data.append({
                    "Claim #": claim.get("patient_control_number", ""),
                    "Line": idx + 1,
                    "CPT": svc.get("cpt_code", ""),
                    "Mods": ", ".join(svc.get("modifiers", [])),
                    "Charge": f"${svc.get('line_item_charge_amount', 0.0):.2f}",
                    "Allowed": f"${allowed_amt:.2f}",
                    "Paid": f"${svc.get('line_item_payment_amount', 0.0):.2f}",
                    "PR": f"${pr_amt:.2f}",
                })

        if services_data:
            lines.append("SERVICES")
            lines.append("-" * 80)
            lines.append(_format_text_table(services_data))

        return "\n".join(lines)


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def _safe_float(x: Optional[Any]) -> float:
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        try:
            return float(str(x))
        except Exception:
            return 0.0


def _parse_cas_adjustments(elements: List[str]) -> List[Dict[str, Any]]:
    """Parse CAS adjustment triplets: reason_code, amount, quantity (optional)."""
    adjustments: List[Dict[str, Any]] = []
    i = 0
    while i + 1 < len(elements):
        reason = elements[i]
        amount = _safe_float(elements[i + 1])
        qty = elements[i + 2] if i + 2 < len(elements) else None
        adjustments.append({"reason": reason, "amount": amount, "quantity": qty})
        i += 3
    return adjustments


def _derive_bill_to_hint(claim_status: Optional[str], patient_responsibility: Optional[float]) -> str:
    status_code = (claim_status or "").strip()
    normalized_status = CLAIM_STATUS_TO_BILL_TO.get(status_code)
    if normalized_status:
        return normalized_status
    pr_value = _safe_float(patient_responsibility)
    if pr_value > 0:
        return BILL_TO_HINT_PATIENT
    return BILL_TO_HINT_PRIMARY


def _format_text_table(rows: List[Dict[str, Any]]) -> str:
    """Format a list of dictionaries as a simple text table."""
    if not rows:
        return ""

    # Get column headers from first row
    headers = list(rows[0].keys())

    # Calculate column widths
    widths = {h: len(str(h)) for h in headers}
    for row in rows:
        for h in headers:
            widths[h] = max(widths[h], len(str(row.get(h, ""))))

    # Build header row
    header_line = "  ".join(str(h).ljust(widths[h]) for h in headers)
    separator = "  ".join("-" * widths[h] for h in headers)

    # Build data rows
    data_lines = []
    for row in rows:
        data_lines.append("  ".join(str(row.get(h, "")).ljust(widths[h]) for h in headers))

    return "\n".join([header_line, separator] + data_lines)

