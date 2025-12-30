"""Tests for X12 835 ERA parser"""

import pytest
from openx12 import x835


class TestParse:
    """Tests for x835.parse() function"""

    def test_returns_object(self, sample_835):
        """Should return parser object"""
        result = x835.parse(sample_835)
        assert result is not None

    def test_has_methods(self, sample_835):
        """Should have json, table, summary methods"""
        result = x835.parse(sample_835)
        assert hasattr(result, 'json')
        assert hasattr(result, 'table')
        assert hasattr(result, 'summary')

    def test_has_properties(self, sample_835):
        """Should have direct access properties"""
        result = x835.parse(sample_835)
        assert hasattr(result, 'claims')
        assert hasattr(result, 'payer')
        assert hasattr(result, 'payee')
        assert hasattr(result, 'payment_amount')
        assert hasattr(result, 'check_number')


class TestJson:
    """Tests for .json() output"""

    def test_file_type(self, sample_835):
        """Should identify file type as 835"""
        result = x835.parse(sample_835).json()
        assert result['file_type'] == '835'

    def test_parsed_at_present(self, sample_835):
        """Should include parsed_at timestamp"""
        result = x835.parse(sample_835).json()
        assert 'parsed_at' in result
        assert result['parsed_at'] is not None

    def test_interchange_header(self, sample_835):
        """Should parse ISA interchange header"""
        result = x835.parse(sample_835).json()
        assert 'interchange' in result
        assert result['interchange']['sender_id'].strip() == 'PAYER'
        assert result['interchange']['receiver_id'].strip() == 'PROVIDER'

    def test_payer_info(self, sample_835):
        """Should extract payer information from N1*PR"""
        era = x835.parse(sample_835)
        assert era.payer['name'] == 'ACME INSURANCE COMPANY'

    def test_payee_info(self, sample_835):
        """Should extract payee information from N1*PE"""
        era = x835.parse(sample_835)
        assert era.payee['name'] == 'BEST MEDICAL CLINIC'

    def test_payment_amount(self, sample_835):
        """Should extract payment amount from BPR"""
        era = x835.parse(sample_835)
        assert era.payment_amount == 500.0

    def test_claims_extracted(self, sample_835):
        """Should extract claims from CLP segments"""
        era = x835.parse(sample_835)
        assert len(era.claims) == 1
        assert era.claims[0]['patient_control_number'] == 'CLM001'

    def test_claim_amounts(self, sample_835):
        """Should extract claim charge and payment amounts"""
        era = x835.parse(sample_835)
        claim = era.claims[0]
        assert claim['total_claim_charge'] == 1000.0
        assert claim['claim_payment_amount'] == 500.0

    def test_claim_status(self, sample_835):
        """Should extract claim status"""
        era = x835.parse(sample_835)
        claim = era.claims[0]
        assert claim['claim_status'] == '1'  # Primary

    def test_services_extracted(self, sample_835):
        """Should extract service lines from SVC segments"""
        era = x835.parse(sample_835)
        claim = era.claims[0]
        assert 'services' in claim
        assert len(claim['services']) == 3

    def test_service_cpt_codes(self, sample_835):
        """Should extract CPT codes from services"""
        era = x835.parse(sample_835)
        services = era.claims[0]['services']
        cpt_codes = [s['cpt_code'] for s in services]
        assert '99213' in cpt_codes
        assert '87880' in cpt_codes
        assert '36415' in cpt_codes

    def test_service_amounts(self, sample_835):
        """Should extract service charge and payment amounts"""
        era = x835.parse(sample_835)
        service = era.claims[0]['services'][0]
        assert service['line_item_charge_amount'] == 200.0
        assert service['line_item_payment_amount'] == 150.0

    def test_adjustments_extracted(self, sample_835):
        """Should extract CAS adjustments"""
        era = x835.parse(sample_835)
        claim = era.claims[0]
        assert 'adjustments' in claim
        assert len(claim['adjustments']) > 0

    def test_patient_responsibility(self, sample_835):
        """Should calculate patient responsibility from PR adjustments"""
        era = x835.parse(sample_835)
        claim = era.claims[0]
        assert claim['patient_responsibility'] > 0

    def test_bill_to_hint(self, sample_835):
        """Should derive bill_to_hint based on claim status"""
        era = x835.parse(sample_835)
        claim = era.claims[0]
        assert 'bill_to_hint' in claim
        # Status 1 (primary) should suggest billing secondary
        assert claim['bill_to_hint'] == 'secondary'

    def test_allowed_amount(self, sample_835):
        """Should extract allowed amount from AMT*AU"""
        era = x835.parse(sample_835)
        claim = era.claims[0]
        # AMT*AU is stored in amounts dict
        assert claim['amounts'].get('AU') == 500.0

    def test_service_amounts(self, sample_835):
        """Should extract service-level amounts from AMT segments"""
        era = x835.parse(sample_835)
        services = era.claims[0]['services']
        # Services have amounts dict with B6 (allowed amount)
        assert services[0]['amounts'].get('B6') == 150.0


class TestSummary:
    """Tests for .summary() output"""

    def test_file_type(self, sample_835):
        """Should include file type"""
        result = x835.parse(sample_835).summary()
        assert '835' in result['file_type']

    def test_payer(self, sample_835):
        """Should include payer name"""
        result = x835.parse(sample_835).summary()
        assert result['payer'] == 'ACME INSURANCE COMPANY'

    def test_payee(self, sample_835):
        """Should include payee name"""
        result = x835.parse(sample_835).summary()
        assert result['payee'] == 'BEST MEDICAL CLINIC'

    def test_totals(self, sample_835):
        """Should include totals"""
        result = x835.parse(sample_835).summary()
        assert result['total_claims'] == 1
        assert result['payment_amount'] == 500.0


class TestTable:
    """Tests for .table() output"""

    def test_returns_string(self, sample_835):
        """Should return a string"""
        result = x835.parse(sample_835).table()
        assert isinstance(result, str)

    def test_has_header(self, sample_835):
        """Should include 835 header"""
        result = x835.parse(sample_835).table()
        assert '835 ERA' in result

    def test_has_claims_section(self, sample_835):
        """Should include CLAIMS section"""
        result = x835.parse(sample_835).table()
        assert 'CLAIMS' in result

    def test_has_services_section(self, sample_835):
        """Should include SERVICES section"""
        result = x835.parse(sample_835).table()
        assert 'SERVICES' in result

    def test_claims_include_claim_number(self, sample_835):
        """Should include claim numbers in output"""
        result = x835.parse(sample_835).table()
        assert 'CLM001' in result

    def test_services_include_cpt_codes(self, sample_835):
        """Should include CPT codes in output"""
        result = x835.parse(sample_835).table()
        assert '99213' in result

    def test_amounts_formatted_with_dollar(self, sample_835):
        """Should format amounts with dollar signs"""
        result = x835.parse(sample_835).table()
        assert '$' in result


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_string(self):
        """Should handle empty string input"""
        era = x835.parse('')
        assert len(era.claims) == 0

    def test_whitespace_only(self):
        """Should handle whitespace-only input"""
        era = x835.parse('   \n\t  ')
        assert era.json()['file_type'] == '835'

    def test_minimal_835(self, minimal_835):
        """Should parse minimal valid 835 file"""
        era = x835.parse(minimal_835)
        assert era.json()['file_type'] == '835'
        assert len(era.claims) == 1

    def test_no_claims(self, minimal_835):
        """Should handle file with no CLP segments"""
        no_claims = minimal_835.replace('CLP*CLM001*1*100*100*0*12*CTL001~', '')
        no_claims = no_claims.replace('SVC*HC:99213*100*100~', '')
        era = x835.parse(no_claims)
        assert len(era.claims) == 0

    def test_malformed_amounts(self):
        """Should handle malformed amount values"""
        bad_data = """ISA*00*          *00*          *ZZ*X*ZZ*Y*231215*1200*^*00501*1*0*P*:~
BPR*I*NOTANUMBER*C*CHK~
CLP*CLM001*1*abc*def*ghi*12*CTL001~
SE*5*0001~
IEA*1*1~"""
        era = x835.parse(bad_data)
        # Should not raise, amounts should be 0.0
        assert era.payment_amount == 0.0
