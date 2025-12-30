"""Tests for X12 837I Institutional Claims parser"""

import pytest
from openx12 import x837i


class TestParse:
    """Tests for x837i.parse() function"""

    def test_returns_object(self, sample_837i):
        """Should return parser object"""
        result = x837i.parse(sample_837i)
        assert result is not None

    def test_has_methods(self, sample_837i):
        """Should have json, table, summary methods"""
        result = x837i.parse(sample_837i)
        assert hasattr(result, 'json')
        assert hasattr(result, 'table')
        assert hasattr(result, 'summary')

    def test_has_properties(self, sample_837i):
        """Should have direct access properties"""
        result = x837i.parse(sample_837i)
        assert hasattr(result, 'claims')
        assert hasattr(result, 'patients')
        assert hasattr(result, 'providers')
        assert hasattr(result, 'total_billed')
        assert hasattr(result, 'billing_facility')


class TestJson:
    """Tests for .json() output"""

    def test_file_type(self, sample_837i):
        """Should identify file type as 837I"""
        result = x837i.parse(sample_837i).json()
        assert result['file_type'] == '837I'

    def test_parsed_at(self, sample_837i):
        """Should include parsed_at timestamp"""
        result = x837i.parse(sample_837i).json()
        assert 'parsed_at' in result

    def test_providers_extracted(self, sample_837i):
        """Should extract billing provider from NM1*85"""
        claim = x837i.parse(sample_837i)
        assert len(claim.providers) >= 1
        assert claim.providers[0]['last_name'] == 'GENERAL HOSPITAL'

    def test_provider_address(self, sample_837i):
        """Should extract provider address from N3/N4"""
        claim = x837i.parse(sample_837i)
        provider = claim.providers[0]
        assert 'address' in provider
        assert provider['address']['city'] == 'HOUSTON'
        assert provider['address']['state'] == 'TX'

    def test_patients_extracted(self, sample_837i):
        """Should extract patient from NM1*IL"""
        claim = x837i.parse(sample_837i)
        assert len(claim.patients) >= 1
        patient = claim.patients[0]
        assert patient['first_name'] == 'ROBERT'
        assert patient['last_name'] == 'JOHNSON'

    def test_patient_demographics(self, sample_837i):
        """Should extract patient demographics from DMG"""
        claim = x837i.parse(sample_837i)
        patient = claim.patients[0]
        assert 'demographics' in patient
        assert patient['demographics']['date_of_birth'] == '1950-01-01'
        assert patient['demographics']['gender'] == 'M'

    def test_claims_extracted(self, sample_837i):
        """Should extract claims from CLM segments"""
        claim = x837i.parse(sample_837i)
        assert len(claim.claims) == 1
        assert claim.claims[0]['claim_number'] == 'HOSP001'

    def test_claim_amount(self, sample_837i):
        """Should extract claim amount"""
        claim = x837i.parse(sample_837i)
        assert claim.claims[0]['amount'] == 25000.0

    def test_institutional_info(self, sample_837i):
        """Should extract institutional info from CL1"""
        claim = x837i.parse(sample_837i)
        inst = claim.claims[0].get('institutional_info', {})
        assert inst['admission_type'] == '1'
        assert inst['admission_source'] == '1'
        assert inst['patient_status'] == '30'

    def test_diagnoses_extracted(self, sample_837i):
        """Should extract diagnoses from HI segments"""
        claim = x837i.parse(sample_837i)
        diagnoses = claim.claims[0]['diagnoses']
        assert len(diagnoses) >= 4

    def test_principal_diagnosis(self, sample_837i):
        """Should identify principal diagnosis (ABK)"""
        claim = x837i.parse(sample_837i)
        diagnoses = claim.claims[0]['diagnoses']
        principal = [d for d in diagnoses if d['type'] == 'principal']
        assert len(principal) >= 1
        assert principal[0]['diagnosis_code'] == 'I2510'

    def test_drg_extracted(self, sample_837i):
        """Should extract DRG from HI*DR"""
        claim = x837i.parse(sample_837i)
        diagnoses = claim.claims[0]['diagnoses']
        drg = [d for d in diagnoses if d['type'] == 'drg']
        assert len(drg) >= 1

    def test_attending_physician(self, sample_837i):
        """Should extract attending physician from NM1*71"""
        claim = x837i.parse(sample_837i)
        attending = claim.claims[0].get('attending_physician', {})
        assert attending.get('last_name') == 'HEART'

    def test_services_extracted(self, sample_837i):
        """Should extract services from SV2 segments"""
        claim = x837i.parse(sample_837i)
        services = claim.claims[0]['services']
        assert len(services) == 4

    def test_revenue_codes(self, sample_837i):
        """Should extract revenue codes from SV2"""
        claim = x837i.parse(sample_837i)
        services = claim.claims[0]['services']
        rev_codes = [s['revenue_code'] for s in services]
        assert '0450' in rev_codes
        assert '0250' in rev_codes


class TestSummary:
    """Tests for .summary() output"""

    def test_file_type(self, sample_837i):
        """Should include file type"""
        result = x837i.parse(sample_837i).summary()
        assert '837I' in result['file_type']

    def test_billing_facility(self, sample_837i):
        """Should include billing facility"""
        result = x837i.parse(sample_837i).summary()
        assert result['billing_facility'] == 'GENERAL HOSPITAL'

    def test_totals(self, sample_837i):
        """Should include totals"""
        result = x837i.parse(sample_837i).summary()
        assert result['total_claims'] == 1
        assert result['total_billed'] == 25000.0

    def test_admission_breakdown(self, sample_837i):
        """Should include admission type breakdown"""
        result = x837i.parse(sample_837i).summary()
        assert 'admission_type_breakdown' in result


class TestTable:
    """Tests for .table() output"""

    def test_returns_string(self, sample_837i):
        """Should return a string"""
        result = x837i.parse(sample_837i).table()
        assert isinstance(result, str)

    def test_has_header(self, sample_837i):
        """Should include 837I header"""
        result = x837i.parse(sample_837i).table()
        assert '837I' in result

    def test_has_claims_section(self, sample_837i):
        """Should include CLAIMS section"""
        result = x837i.parse(sample_837i).table()
        assert 'CLAIMS' in result

    def test_has_services_section(self, sample_837i):
        """Should include SERVICES section"""
        result = x837i.parse(sample_837i).table()
        assert 'SERVICES' in result

    def test_has_patients_section(self, sample_837i):
        """Should include PATIENTS section"""
        result = x837i.parse(sample_837i).table()
        assert 'PATIENTS' in result

    def test_has_providers_section(self, sample_837i):
        """Should include PROVIDERS section"""
        result = x837i.parse(sample_837i).table()
        assert 'PROVIDERS' in result

    def test_claims_include_claim_number(self, sample_837i):
        """Should include claim numbers in output"""
        result = x837i.parse(sample_837i).table()
        assert 'HOSP001' in result

    def test_revenue_codes_included(self, sample_837i):
        """Should include revenue codes in output"""
        result = x837i.parse(sample_837i).table()
        assert '0450' in result

    def test_amounts_formatted_with_dollar(self, sample_837i):
        """Should format amounts with dollar signs"""
        result = x837i.parse(sample_837i).table()
        assert '$' in result


class TestEdgeCases:
    """Test edge cases"""

    def test_empty_string(self):
        """Should handle empty string"""
        result = x837i.parse('')
        assert len(result.claims) == 0

    def test_minimal_file(self, minimal_837i):
        """Should parse minimal valid file"""
        claim = x837i.parse(minimal_837i)
        assert len(claim.claims) == 1
        assert 'institutional_info' in claim.claims[0]
