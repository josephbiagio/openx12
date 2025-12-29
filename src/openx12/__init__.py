"""
openx12 - Python library for parsing X12 healthcare EDI files

Supports:
- 835 (ERA/Remittance Advice)
- 837P (Professional Claims)
- 837I (Institutional Claims)

Usage:
    from openx12 import x835, x837p, x837i

    # 835 ERA
    era = x835.parse(content)
    era.summary()
    era.json()
    era.table()
    era.claims
    era.payer

    # 837P Professional
    claim = x837p.parse(content)
    claim.summary()
    claim.claims
    claim.total_billed

    # 837I Institutional
    claim = x837i.parse(content)
    claim.summary()
    claim.claims
"""

from . import x835
from . import x837p
from . import x837i

__version__ = "0.2.0"
__all__ = ["x835", "x837p", "x837i"]
