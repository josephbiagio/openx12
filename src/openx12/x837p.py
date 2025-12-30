"""
837P Professional Claims Parser

Parse X12 837P files into structured data with multiple output formats.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


def parse(content: str) -> "Claim837P":
    """Parse 837P professional claim content and return parser object."""
    return Claim837P(content)


def _to_float(value: str) -> float:
    """Safely convert string to float."""
    try:
        return float(value)
    except Exception:
        return 0.0


def _format_date(date_str: str) -> str:
    """Convert CCYYMMDD to YYYY-MM-DD format."""
    if date_str and len(date_str) == 8:
        try:
            return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except Exception:
            pass
    return date_str


class Claim837P:
    """
    Parse and access X12 837P (Professional Claims) data.

    Usage:
        claim = Claim837P(edi_content)
        claim.summary()    # Quick overview
        claim.json()       # Full structured data
        claim.table()      # Display-friendly tables

        # Direct access
        claim.claims
        claim.patients
        claim.providers
        claim.total_billed
    """

    def __init__(self, content: str):
        self.content = content.strip().replace('\n', '').replace('\r', '')
        self._segments = self._split_segments()
        self._parsed: Optional[Dict[str, Any]] = None
        self._parse()

    def _split_segments(self) -> List[str]:
        return [seg.strip() for seg in self.content.split('~') if seg.strip()]

    def _parse_segment(self, segment: str) -> Dict[str, Any]:
        if not segment:
            return {}
        elements = segment.split('*')
        return {
            'segment_id': elements[0] if elements else '',
            'elements': elements[1:] if len(elements) > 1 else [],
            'raw': segment
        }

    def _parse(self) -> None:
        """Parse all segments into structured data."""
        result = {
            'file_type': '837P',
            'parsed_at': datetime.now().isoformat(),
            'segments': [],
            'summary': {
                'total_segments': len(self._segments),
                'claims': [],
                'providers': [],
                'patients': []
            }
        }

        current_claim: Optional[Dict[str, Any]] = None
        current_patient: Optional[Dict[str, Any]] = None
        current_provider: Optional[Dict[str, Any]] = None
        current_entity: Optional[Dict[str, Any]] = None
        current_service: Optional[Dict[str, Any]] = None

        for segment_raw in self._segments:
            segment = self._parse_segment(segment_raw)
            result['segments'].append(segment)

            seg_id = segment['segment_id']
            elements = segment['elements']

            if seg_id == 'ISA':
                result['interchange'] = self._parse_isa(elements)
            elif seg_id == 'GS':
                result['group'] = self._parse_gs(elements)
            elif seg_id == 'ST':
                result['transaction'] = self._parse_st(elements)
            elif seg_id == 'BHT':
                result['batch_header'] = self._parse_bht(elements)
            elif seg_id == 'NM1':
                entity = self._parse_nm1(elements)
                entity_type = entity['entity_type']
                current_entity = entity

                if entity_type == '85':  # Billing Provider
                    current_provider = entity
                    result['summary']['providers'].append(entity)
                elif entity_type == 'IL':  # Insured/Subscriber
                    current_patient = entity
                    result['summary']['patients'].append(entity)
                elif entity_type == 'QC':  # Patient
                    current_patient = entity
                    result['summary']['patients'].append(entity)
                elif entity_type == 'PR':  # Payer
                    if current_claim:
                        current_claim['payer'] = entity

            elif seg_id == 'N3' and current_entity:
                address = current_entity.setdefault('address', {})
                address['line1'] = elements[0] if len(elements) > 0 else ''
                if len(elements) > 1 and elements[1]:
                    address['line2'] = elements[1]

            elif seg_id == 'N4' and current_entity:
                address = current_entity.setdefault('address', {})
                address['city'] = elements[0] if len(elements) > 0 else ''
                address['state'] = elements[1] if len(elements) > 1 else ''
                address['zip'] = elements[2] if len(elements) > 2 else ''
                if len(elements) > 3 and elements[3]:
                    address['country'] = elements[3]

            elif seg_id == 'DMG' and current_patient:
                current_patient['demographics'] = self._parse_dmg(elements)

            elif seg_id == 'REF':
                if len(elements) >= 2:
                    ref_qualifier = elements[0]
                    ref_value = elements[1]
                    if ref_qualifier == 'MI' and current_patient:
                        current_patient['subscriber_id'] = ref_value
                    elif ref_qualifier == 'EI' and current_provider:
                        current_provider['tax_id'] = ref_value
                    elif current_claim:
                        refs = current_claim.setdefault('references', {})
                        refs[ref_qualifier] = ref_value

            elif seg_id == 'SBR':
                sbr_info = self._parse_sbr(elements)
                if current_claim:
                    current_claim['subscriber_info'] = sbr_info
                else:
                    result['_pending_sbr'] = sbr_info

            elif seg_id == 'CLM':
                current_claim = self._parse_clm(elements)
                current_service = None
                if result.get('_pending_sbr'):
                    current_claim['subscriber_info'] = result.pop('_pending_sbr')
                result['summary']['claims'].append(current_claim)

            elif seg_id == 'DTP' and current_claim:
                self._apply_dtp(current_claim, current_service, elements)

            elif seg_id == 'NTE' and current_claim:
                note = self._parse_nte(elements)
                if note:
                    notes = current_claim.setdefault('notes', [])
                    notes.append(note)

            elif seg_id == 'HI' and current_claim:
                diagnoses = self._parse_hi(elements)
                if diagnoses:
                    claim_dx = current_claim.setdefault('diagnoses', [])
                    claim_dx.extend(diagnoses)

            elif seg_id == 'SV1' and current_claim:
                service = self._parse_sv1(elements)
                current_service = service
                services = current_claim.setdefault('services', [])
                services.append(service)

            elif seg_id == 'LX' and current_claim:
                current_service = None

        result.pop('_pending_sbr', None)
        self._parsed = result

    # -------------------------------------------------------------------------
    # Segment Parsers
    # -------------------------------------------------------------------------

    def _parse_isa(self, elements: List[str]) -> Dict[str, Any]:
        return {
            'authorization_qualifier': elements[0] if len(elements) > 0 else '',
            'authorization_info': elements[1] if len(elements) > 1 else '',
            'security_qualifier': elements[2] if len(elements) > 2 else '',
            'security_info': elements[3] if len(elements) > 3 else '',
            'sender_qualifier': elements[4] if len(elements) > 4 else '',
            'sender_id': elements[5] if len(elements) > 5 else '',
            'receiver_qualifier': elements[6] if len(elements) > 6 else '',
            'receiver_id': elements[7] if len(elements) > 7 else '',
            'date': elements[8] if len(elements) > 8 else '',
            'time': elements[9] if len(elements) > 9 else '',
            'control_number': elements[12] if len(elements) > 12 else '',
            'production_flag': elements[14] if len(elements) > 14 else ''
        }

    def _parse_gs(self, elements: List[str]) -> Dict[str, Any]:
        return {
            'functional_id': elements[0] if len(elements) > 0 else '',
            'sender_code': elements[1] if len(elements) > 1 else '',
            'receiver_code': elements[2] if len(elements) > 2 else '',
            'date': elements[3] if len(elements) > 3 else '',
            'time': elements[4] if len(elements) > 4 else '',
            'control_number': elements[5] if len(elements) > 5 else '',
            'version': elements[7] if len(elements) > 7 else ''
        }

    def _parse_st(self, elements: List[str]) -> Dict[str, Any]:
        return {
            'transaction_type': elements[0] if len(elements) > 0 else '',
            'control_number': elements[1] if len(elements) > 1 else '',
            'version': elements[2] if len(elements) > 2 else ''
        }

    def _parse_bht(self, elements: List[str]) -> Dict[str, Any]:
        return {
            'structure_code': elements[0] if len(elements) > 0 else '',
            'purpose_code': elements[1] if len(elements) > 1 else '',
            'reference_id': elements[2] if len(elements) > 2 else '',
            'date': elements[3] if len(elements) > 3 else '',
            'time': elements[4] if len(elements) > 4 else ''
        }

    def _parse_nm1(self, elements: List[str]) -> Dict[str, Any]:
        return {
            'entity_type': elements[0] if len(elements) > 0 else '',
            'entity_type_qualifier': elements[1] if len(elements) > 1 else '',
            'last_name': elements[2] if len(elements) > 2 else '',
            'first_name': elements[3] if len(elements) > 3 else '',
            'middle_name': elements[4] if len(elements) > 4 else '',
            'suffix': elements[6] if len(elements) > 6 else '',
            'id_qualifier': elements[7] if len(elements) > 7 else '',
            'id_value': elements[8] if len(elements) > 8 else ''
        }

    def _parse_dmg(self, elements: List[str]) -> Dict[str, Any]:
        dob_raw = elements[1] if len(elements) > 1 else ''
        return {
            'date_format': elements[0] if len(elements) > 0 else '',
            'date_of_birth': _format_date(dob_raw),
            'gender': elements[2] if len(elements) > 2 else ''
        }

    def _parse_sbr(self, elements: List[str]) -> Dict[str, Any]:
        return {
            'payer_sequence': elements[0] if len(elements) > 0 else '',
            'relationship_code': elements[1] if len(elements) > 1 else '',
            'group_number': elements[2] if len(elements) > 2 else '',
            'group_name': elements[3] if len(elements) > 3 else '',
            'insurance_type': elements[4] if len(elements) > 4 else '',
            'filing_indicator': elements[8] if len(elements) > 8 else ''
        }

    def _parse_nte(self, elements: List[str]) -> Optional[Dict[str, Any]]:
        if not elements:
            return None
        return {
            'type': elements[0] if len(elements) > 0 else '',
            'text': elements[1] if len(elements) > 1 else ''
        }

    def _apply_dtp(self, claim: Dict[str, Any], service: Optional[Dict[str, Any]], elements: List[str]) -> None:
        if len(elements) < 3:
            return

        qualifier = elements[0]
        date_format = elements[1]
        date_value = elements[2]

        dates = claim.setdefault('dates', {})

        if date_format == 'D8' and len(date_value) == 8:
            date_value = _format_date(date_value)
        elif date_format == 'RD8' and '-' in date_value:
            parts = date_value.split('-')
            if len(parts) == 2:
                date_value = f"{_format_date(parts[0])} to {_format_date(parts[1])}"

        qualifier_map = {
            '472': 'service_date',
            '431': 'onset_date',
            '454': 'initial_treatment_date',
            '304': 'latest_visit_date',
            '435': 'admission_date',
            '096': 'discharge_hour',
            '434': 'statement_from_date',
            '050': 'received_date',
            '471': 'prescription_date',
        }

        field_name = qualifier_map.get(qualifier, f'date_{qualifier}')

        if service and qualifier == '472':
            service['service_date'] = date_value
        else:
            dates[field_name] = date_value

    def _parse_clm(self, elements: List[str]) -> Dict[str, Any]:
        facility_info = elements[4] if len(elements) > 4 else ''
        place_of_service = ''
        facility_qualifier = ''
        frequency = ''

        if ':' in facility_info:
            parts = facility_info.split(':')
            place_of_service = parts[0] if len(parts) > 0 else ''
            facility_qualifier = parts[1] if len(parts) > 1 else ''
            frequency = parts[2] if len(parts) > 2 else ''

        return {
            'claim_number': elements[0] if len(elements) > 0 else '',
            'amount': _to_float(elements[1]) if len(elements) > 1 and elements[1] else 0.0,
            'place_of_service': place_of_service,
            'facility_qualifier': facility_qualifier,
            'frequency': frequency,
            'provider_signature': elements[5] if len(elements) > 5 else '',
            'assignment_code': elements[6] if len(elements) > 6 else '',
            'benefits_assignment': elements[7] if len(elements) > 7 else '',
            'release_info': elements[8] if len(elements) > 8 else ''
        }

    def _parse_sv1(self, elements: List[str]) -> Dict[str, Any]:
        procedure_info = elements[0] if len(elements) > 0 else ''
        procedure_qualifier = ''
        cpt_code = ''
        modifiers: List[str] = []

        if ':' in procedure_info:
            parts = procedure_info.split(':')
            procedure_qualifier = parts[0] if len(parts) > 0 else ''
            cpt_code = parts[1] if len(parts) > 1 else ''
            modifiers = [p for p in parts[2:6] if p]

        return {
            'procedure_qualifier': procedure_qualifier,
            'cpt_code': cpt_code,
            'modifiers': modifiers,
            'charge': _to_float(elements[1]) if len(elements) > 1 and elements[1] else 0.0,
            'unit_type': elements[2] if len(elements) > 2 else '',
            'units': elements[3] if len(elements) > 3 else '1',
            'place_of_service': elements[4] if len(elements) > 4 else '',
            'diagnosis_pointers': elements[6].split(':') if len(elements) > 6 and elements[6] else []
        }

    def _parse_hi(self, elements: List[str]) -> List[Dict[str, Any]]:
        diagnoses = []
        is_first = True

        for element in elements:
            if not element:
                continue

            if ':' in element:
                parts = element.split(':')
                qualifier = parts[0]
                code = parts[1] if len(parts) > 1 else ''

                diagnoses.append({
                    'qualifier': qualifier,
                    'diagnosis_code': code,
                    'type': 'primary' if (qualifier == 'ABK' or (qualifier == 'ABF' and is_first)) else 'secondary'
                })
                is_first = False

        return diagnoses

    # -------------------------------------------------------------------------
    # Public Properties
    # -------------------------------------------------------------------------

    @property
    def claims(self) -> List[Dict[str, Any]]:
        """List of all claims."""
        return self._parsed.get('summary', {}).get('claims', [])

    @property
    def patients(self) -> List[Dict[str, Any]]:
        """List of all patients."""
        return self._parsed.get('summary', {}).get('patients', [])

    @property
    def providers(self) -> List[Dict[str, Any]]:
        """List of all providers."""
        return self._parsed.get('summary', {}).get('providers', [])

    @property
    def total_billed(self) -> float:
        """Total billed amount across all claims."""
        return sum(c.get('amount', 0) for c in self.claims)

    @property
    def billing_provider(self) -> Dict[str, Any]:
        """First/primary billing provider."""
        return self.providers[0] if self.providers else {}

    # -------------------------------------------------------------------------
    # Output Methods
    # -------------------------------------------------------------------------

    def json(self) -> Dict[str, Any]:
        """Return full parsed data as structured dictionary."""
        return self._parsed

    def summary(self) -> Dict[str, Any]:
        """Return concise summary with key information."""
        all_dates = []
        for claim in self.claims:
            dates = claim.get('dates', {})
            if dates.get('service_date'):
                all_dates.append(dates['service_date'])
            if dates.get('service_date_end'):
                all_dates.append(dates['service_date_end'])
            for svc in claim.get('services', []):
                if svc.get('service_date'):
                    all_dates.append(svc['service_date'])

        date_range = ""
        if all_dates:
            all_dates.sort()
            if all_dates[0] == all_dates[-1]:
                date_range = all_dates[0]
            else:
                date_range = f"{all_dates[0]} to {all_dates[-1]}"

        return {
            'file_type': '837P (Professional Claim)',
            'submitter': self._parsed.get('interchange', {}).get('sender_id', '').strip(),
            'receiver': self._parsed.get('interchange', {}).get('receiver_id', '').strip(),
            'billing_provider': self.billing_provider.get('last_name', ''),
            'billing_npi': self.billing_provider.get('id_value', ''),
            'total_claims': len(self.claims),
            'total_patients': len(self.patients),
            'total_billed': self.total_billed,
            'service_date_range': date_range,
            'total_services': sum(len(c.get('services', [])) for c in self.claims),
            'total_diagnoses': sum(len(c.get('diagnoses', [])) for c in self.claims),
        }

    def table(self) -> str:
        """Return display-friendly formatted text table."""
        lines: List[str] = []

        # File info header
        lines.append("=" * 80)
        lines.append("837P Professional Claim")
        lines.append("=" * 80)
        lines.append(f"Provider:       {self.billing_provider.get('last_name', 'N/A')}")
        lines.append(f"NPI:            {self.billing_provider.get('id_value', 'N/A')}")
        lines.append(f"Total Claims:   {len(self.claims)}")
        lines.append(f"Total Billed:   ${self.total_billed:.2f}")
        lines.append("")

        # Claims table
        claims_data = []
        for claim in self.claims:
            dates = claim.get('dates', {})
            sbr = claim.get('subscriber_info', {})
            claims_data.append({
                'Claim #': claim.get('claim_number', ''),
                'Amount': f"${claim.get('amount', 0):.2f}",
                'POS': claim.get('place_of_service', ''),
                'Date': dates.get('service_date', ''),
                'Payer Seq': sbr.get('payer_sequence', ''),
                'Services': len(claim.get('services', [])),
                'Dx': len(claim.get('diagnoses', []))
            })

        if claims_data:
            lines.append("CLAIMS")
            lines.append("-" * 80)
            lines.append(_format_text_table(claims_data))
            lines.append("")

        # Services table
        services_data = []
        for claim in self.claims:
            for i, service in enumerate(claim.get('services', [])):
                services_data.append({
                    'Claim #': claim.get('claim_number', ''),
                    'Line': i + 1,
                    'CPT': service.get('cpt_code', ''),
                    'Mods': ', '.join(service.get('modifiers', [])),
                    'Charge': f"${service.get('charge', 0):.2f}",
                    'Units': service.get('units', '1'),
                    'Date': service.get('service_date', ''),
                })

        if services_data:
            lines.append("SERVICES")
            lines.append("-" * 80)
            lines.append(_format_text_table(services_data))
            lines.append("")

        # Patients table
        patients_data = []
        for patient in self.patients:
            demographics = patient.get('demographics', {})
            address = patient.get('address', {})
            patients_data.append({
                'Name': f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                'ID': patient.get('subscriber_id', '') or patient.get('id_value', ''),
                'DOB': demographics.get('date_of_birth', ''),
                'Gender': demographics.get('gender', ''),
                'City': address.get('city', ''),
                'State': address.get('state', '')
            })

        if patients_data:
            lines.append("PATIENTS")
            lines.append("-" * 80)
            lines.append(_format_text_table(patients_data))
            lines.append("")

        # Providers table
        providers_data = []
        for provider in self.providers:
            address = provider.get('address', {})
            providers_data.append({
                'Name': provider.get('last_name', ''),
                'NPI': provider.get('id_value', ''),
                'Tax ID': provider.get('tax_id', ''),
                'City': address.get('city', ''),
                'State': address.get('state', '')
            })

        if providers_data:
            lines.append("PROVIDERS")
            lines.append("-" * 80)
            lines.append(_format_text_table(providers_data))

        return "\n".join(lines)


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

