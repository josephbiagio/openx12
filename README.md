```
█▀█ █▀█ █▀▀ █▄ █ ▀▄▀ ▄█ ▀█
█▄█ █▀▀ ██▄ █ ▀█ █ █  █ █▄
```

<p align="center">
  <strong>Parse X12 healthcare EDI files with Python</strong><br>
  <sub>835 (ERA) • 837P (Professional) • 837I (Institutional)</sub>
</p>

<p align="center">
  <a href="https://github.com/josephbiagio/openx12">
    <img src="https://img.shields.io/badge/github-josephbiagio%2Fopenx12-blue?logo=github" alt="GitHub">
  </a>
  <a href="https://pypi.org/project/openx12">
    <img src="https://img.shields.io/pypi/v/openx12?color=green" alt="PyPI">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  </a>
</p>

---

## Features

- **Zero dependencies** - Uses only Python standard library
- **Clean API** - `x835.parse(content).summary()`
- **Multiple outputs** - `.json()`, `.table()`, `.summary()`
- **Direct access** - `.claims`, `.payer`, `.total_billed`
- **CLI included** - Parse files from command line

## Installation

```bash
pip install openx12
```

## Quick Start

```python
from openx12 import x835, x837p, x837i

# Parse an 835 ERA file
era = x835.parse(edi_content)
print(era.summary())
print(f"Payment: ${era.payment_amount}")
print(f"Payer: {era.payer['name']}")

# Parse an 837P professional claim
claim = x837p.parse(edi_content)
print(claim.summary())
print(f"Total Billed: ${claim.total_billed}")
print(f"Claims: {len(claim.claims)}")

# Parse an 837I institutional claim
claim = x837i.parse(edi_content)
print(claim.summary())
print(f"Facility: {claim.billing_facility['last_name']}")
```

## Output Methods

Each parser returns an object with three output methods:

```python
claim = x837p.parse(content)

# Quick overview
claim.summary()

# Full structured data
claim.json()

# Display-friendly tables
claim.table()
```

## Direct Property Access

Access parsed data directly without calling methods:

```python
# 835 ERA
era = x835.parse(content)
era.payer           # {'name': 'ACME INSURANCE', 'id': '12345'}
era.payee           # {'name': 'MEDICAL CLINIC', 'id': '67890'}
era.claims          # List of all claims
era.payment_amount  # 1500.00
era.check_number    # '123456789'

# 837P Professional
claim = x837p.parse(content)
claim.claims           # List of all claims
claim.patients         # List of all patients
claim.providers        # List of all providers
claim.total_billed     # 72663.87
claim.billing_provider # First provider dict

# 837I Institutional
claim = x837i.parse(content)
claim.claims           # List of all claims
claim.patients         # List of all patients
claim.providers        # List of all providers
claim.total_billed     # 250000.00
claim.billing_facility # First facility dict
```

## CLI Usage

```bash
# Parse with auto-detect
openx12 parse remittance.835

# Get summary
openx12 parse claim.edi -f summary

# Specify type
openx12 parse claim.edi -t 837p

# Output as table format
openx12 parse era.txt -f table

# Save to file
openx12 parse input.835 -o output.json

# Read from stdin
cat file.835 | openx12 parse -
```

## Output Structures

### .summary()

```python
# 835 ERA
{
    "file_type": "835 (ERA/Remittance)",
    "payer": "ACME INSURANCE",
    "payee": "MEDICAL CLINIC",
    "check_number": "123456789",
    "payment_amount": 1500.00,
    "total_claims": 5,
    "total_charged": 2000.00,
    "total_paid": 1500.00,
    "total_patient_responsibility": 300.00
}

# 837P Professional
{
    "file_type": "837P (Professional Claim)",
    "billing_provider": "SEQUOIA FAMILY MEDICAL CENTER",
    "billing_npi": "1790221703",
    "total_claims": 592,
    "total_patients": 631,
    "total_billed": 72663.87,
    "service_date_range": "2024-12-13 to 2025-12-03",
    "total_services": 1346
}

# 837I Institutional
{
    "file_type": "837I (Institutional Claim)",
    "billing_facility": "GENERAL HOSPITAL",
    "billing_npi": "1234567890",
    "total_claims": 10,
    "total_billed": 250000.00,
    "admission_type_breakdown": {"1": 3, "3": 7}
}
```

### .json()

Returns full parsed data including:
- All segments parsed
- Interchange/group headers
- Claims with services, diagnoses, dates
- Providers with addresses
- Patients with demographics

### .table()

Returns a formatted text table string for display:
```
================================================================================
837P Professional Claim
================================================================================
Provider:       PREMIER MEDICAL GROUP
NPI:            1234567890
Total Claims:   1
Total Billed:   $350.00

CLAIMS
--------------------------------------------------------------------------------
Claim #   Amount    POS  Date        Payer Seq  Services  Dx
--------  --------  ---  ----------  ---------  --------  --
CLAIM001  $350.00   11   2023-12-10  P          3         3

SERVICES
--------------------------------------------------------------------------------
Claim #   Line  CPT    Mods  Charge    Units  Date
--------  ----  -----  ----  --------  -----  ----------
CLAIM001  1     99214  25    $150.00   1      2023-12-10
CLAIM001  2     36415        $50.00    1      2023-12-10
CLAIM001  3     80053        $150.00   1      2023-12-10
```

## Supported Transactions

| Code | Name | Description |
|------|------|-------------|
| 835 | ERA | Electronic Remittance Advice (payment/denial info) |
| 837P | Professional | Physician/outpatient claims (CMS-1500 equivalent) |
| 837I | Institutional | Hospital/facility claims (UB-04 equivalent) |

## Development

```bash
git clone https://github.com/josephbiagio/openx12.git
cd openx12
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT © [Joseph Biagio](https://github.com/josephbiagio)
