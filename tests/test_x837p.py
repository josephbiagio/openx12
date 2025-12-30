"""Tests for X12 837P Professional Claims parser"""

import pytest
from openx12 import x837p


class TestParse:
    """Tests for x837p.parse() function"""

    def test_returns_object(self, sample_837p):
        """Should return parser object"""
        result = x837p.parse(sample_837p)
        assert result is not None

    def test_has_methods(self, sample_837p):
        """Should have json, table, summary methods"""
        result = x837p.parse(sample_837p)
        assert hasattr(result, 'json')
        assert hasattr(result, 'table')
        assert hasattr(result, 'summary')

    def test_has_properties(self, sample_837p):
        """Should have direct access properties"""
        result = x837p.parse(sample_837p)
        assert hasattr(result, 'claims')
        assert hasattr(result, 'patients')
        assert hasattr(result, 'providers')
        assert hasattr(result, 'total_billed')
        assert hasattr(result, 'billing_provider')


class TestJson:
    """Tests for .json() output"""

    def test_file_type(self, sample_837p):
        """Should identify file type as 837P"""
        result = x837p.parse(sample_837p).json()
        assert result['file_type'] == '837P'

    def test_parsed_at(self, sample_837p):
        """Should include parsed_at timestamp"""
        result = x837p.parse(sample_837p).json()
        assert 'parsed_at' in result

    def test_interchange_header(self, sample_837p):
        """Should parse ISA interchange header"""
        result = x837p.parse(sample_837p).json()
        assert 'interchange' in result
        assert result['interchange']['sender_id'].strip() == 'SENDER'

    def test_batch_header(self, sample_837p):
        """Should parse BHT batch header"""
        result = x837p.parse(sample_837p).json()
        assert 'batch_header' in result
        assert result['batch_header']['reference_id'] == 'BATCH001'

    def test_providers_extracted(self, sample_837p):
        """Should extract billing provider from NM1*85"""
        claim = x837p.parse(sample_837p)
        assert len(claim.providers) >= 1
        assert claim.providers[0]['last_name'] == 'PREMIER MEDICAL GROUP'
        assert claim.providers[0]['id_value'] == '1234567890'

    def test_provider_address(self, sample_837p):
        """Should extract provider address from N3/N4"""
        claim = x837p.parse(sample_837p)
        provider = claim.providers[0]
        assert 'address' in provider
        assert provider['address']['line1'] == '100 MEDICAL PLAZA'
        assert provider['address']['line2'] == 'SUITE 200'
        assert provider['address']['city'] == 'LOS ANGELES'
        assert provider['address']['state'] == 'CA'
        assert provider['address']['zip'] == '90001'

    def test_provider_tax_id(self, sample_837p):
        """Should extract provider tax ID from REF*EI"""
        claim = x837p.parse(sample_837p)
        provider = claim.providers[0]
        assert provider.get('tax_id') == '987654321'

    def test_patients_extracted(self, sample_837p):
        """Should extract patient from NM1*IL"""
        claim = x837p.parse(sample_837p)
        assert len(claim.patients) >= 1
        patient = claim.patients[0]
        assert patient['first_name'] == 'JOHN'
        assert patient['last_name'] == 'SMITH'

    def test_patient_address(self, sample_837p):
        """Should extract patient address from N3/N4"""
        claim = x837p.parse(sample_837p)
        patient = claim.patients[0]
        assert 'address' in patient
        assert patient['address']['city'] == 'LOS ANGELES'
        assert patient['address']['state'] == 'CA'

    def test_patient_demographics(self, sample_837p):
        """Should extract patient demographics from DMG"""
        claim = x837p.parse(sample_837p)
        patient = claim.patients[0]
        assert 'demographics' in patient
        assert patient['demographics']['date_of_birth'] == '1980-05-15'
        assert patient['demographics']['gender'] == 'M'

    def test_claims_extracted(self, sample_837p):
        """Should extract claims from CLM segments"""
        claim = x837p.parse(sample_837p)
        assert len(claim.claims) == 1
        assert claim.claims[0]['claim_number'] == 'CLAIM001'

    def test_claim_amount(self, sample_837p):
        """Should extract claim amount"""
        claim = x837p.parse(sample_837p)
        assert claim.claims[0]['amount'] == 350.0

    def test_claim_place_of_service(self, sample_837p):
        """Should extract place of service"""
        claim = x837p.parse(sample_837p)
        assert claim.claims[0]['place_of_service'] == '11'  # Office

    def test_subscriber_info(self, sample_837p):
        """Should extract subscriber info from SBR"""
        claim = x837p.parse(sample_837p)
        sub = claim.claims[0].get('subscriber_info', {})
        assert sub['payer_sequence'] == 'P'
        assert sub['group_number'] == 'GRP001'

    def test_claim_dates(self, sample_837p):
        """Should extract dates from DTP segments"""
        claim = x837p.parse(sample_837p)
        dates = claim.claims[0].get('dates', {})
        assert dates.get('onset_date') == '2023-12-01'
        assert dates.get('service_date') == '2023-12-10'

    def test_claim_notes(self, sample_837p):
        """Should extract notes from NTE segments"""
        claim = x837p.parse(sample_837p)
        notes = claim.claims[0].get('notes', [])
        assert len(notes) >= 1
        assert notes[0]['type'] == 'ADD'

    def test_diagnoses_extracted(self, sample_837p):
        """Should extract diagnoses from HI segments"""
        claim = x837p.parse(sample_837p)
        diagnoses = claim.claims[0]['diagnoses']
        assert len(diagnoses) == 3

    def test_diagnosis_codes(self, sample_837p):
        """Should extract diagnosis codes correctly"""
        claim = x837p.parse(sample_837p)
        diagnoses = claim.claims[0]['diagnoses']
        codes = [d['diagnosis_code'] for d in diagnoses]
        assert 'E119' in codes  # Type 2 diabetes
        assert 'I10' in codes   # Hypertension
        assert 'E785' in codes  # Hyperlipidemia

    def test_diagnosis_types(self, sample_837p):
        """Should identify primary vs secondary diagnoses"""
        claim = x837p.parse(sample_837p)
        diagnoses = claim.claims[0]['diagnoses']
        types = [d['type'] for d in diagnoses]
        assert 'primary' in types

    def test_services_extracted(self, sample_837p):
        """Should extract services from SV1 segments"""
        claim = x837p.parse(sample_837p)
        services = claim.claims[0]['services']
        assert len(services) == 3

    def test_service_cpt_codes(self, sample_837p):
        """Should extract CPT codes from services"""
        claim = x837p.parse(sample_837p)
        services = claim.claims[0]['services']
        cpt_codes = [s['cpt_code'] for s in services]
        assert '99214' in cpt_codes
        assert '36415' in cpt_codes
        assert '80053' in cpt_codes

    def test_service_modifiers(self, sample_837p):
        """Should extract modifiers from services"""
        claim = x837p.parse(sample_837p)
        services = claim.claims[0]['services']
        # First service should have modifier 25
        assert '25' in services[0]['modifiers']

    def test_service_charges(self, sample_837p):
        """Should extract service charges"""
        claim = x837p.parse(sample_837p)
        services = claim.claims[0]['services']
        assert services[0]['charge'] == 150.0
        assert services[1]['charge'] == 50.0
        assert services[2]['charge'] == 150.0


class TestSummary:
    """Tests for .summary() output"""

    def test_file_type(self, sample_837p):
        """Should include file type"""
        result = x837p.parse(sample_837p).summary()
        assert '837P' in result['file_type']

    def test_billing_provider(self, sample_837p):
        """Should include billing provider"""
        result = x837p.parse(sample_837p).summary()
        assert result['billing_provider'] == 'PREMIER MEDICAL GROUP'

    def test_totals(self, sample_837p):
        """Should include totals"""
        result = x837p.parse(sample_837p).summary()
        assert result['total_claims'] == 1
        assert result['total_billed'] == 350.0


class TestTable:
    """Tests for .table() output"""

    def test_returns_string(self, sample_837p):
        """Should return a string"""
        result = x837p.parse(sample_837p).table()
        assert isinstance(result, str)

    def test_has_header(self, sample_837p):
        """Should include 837P header"""
        result = x837p.parse(sample_837p).table()
        assert '837P' in result

    def test_has_claims_section(self, sample_837p):
        """Should include CLAIMS section"""
        result = x837p.parse(sample_837p).table()
        assert 'CLAIMS' in result

    def test_has_services_section(self, sample_837p):
        """Should include SERVICES section"""
        result = x837p.parse(sample_837p).table()
        assert 'SERVICES' in result

    def test_has_patients_section(self, sample_837p):
        """Should include PATIENTS section"""
        result = x837p.parse(sample_837p).table()
        assert 'PATIENTS' in result

    def test_has_providers_section(self, sample_837p):
        """Should include PROVIDERS section"""
        result = x837p.parse(sample_837p).table()
        assert 'PROVIDERS' in result

    def test_claims_include_claim_number(self, sample_837p):
        """Should include claim numbers in output"""
        result = x837p.parse(sample_837p).table()
        assert 'CLAIM001' in result

    def test_amounts_formatted_with_dollar(self, sample_837p):
        """Should format amounts with dollar signs"""
        result = x837p.parse(sample_837p).table()
        assert '$' in result

    def test_patient_info_included(self, sample_837p):
        """Should include patient information"""
        result = x837p.parse(sample_837p).table()
        assert 'JOHN' in result or 'SMITH' in result

    def test_provider_info_included(self, sample_837p):
        """Should include provider information"""
        result = x837p.parse(sample_837p).table()
        assert 'PREMIER MEDICAL GROUP' in result


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_string(self):
        """Should handle empty string input"""
        claim = x837p.parse('')
        assert len(claim.claims) == 0

    def test_minimal_837p(self, minimal_837p):
        """Should parse minimal valid 837P file"""
        claim = x837p.parse(minimal_837p)
        assert claim.json()['file_type'] == '837P'
        assert len(claim.claims) == 1

    def test_no_diagnoses(self, minimal_837p):
        """Should handle claims without HI segments"""
        no_hi = minimal_837p.replace('HI*ABK:J069~', '')
        claim = x837p.parse(no_hi)
        assert claim.claims[0].get('diagnoses', []) == []

    def test_multiple_modifiers(self):
        """Should handle multiple modifiers on service"""
        data = """ISA*00*          *00*          *ZZ*X*ZZ*Y*231215*1200*^*00501*1*0*P*:~
NM1*85*2*PROV*****XX*123~
CLM*CLM001*100***11:B:1*Y*A*Y*Y~
SV1*HC:99214:25:59:76:77*100*UN*1***1~
SE*5*0001~
IEA*1*1~"""
        claim = x837p.parse(data)
        service = claim.claims[0]['services'][0]
        assert len(service['modifiers']) == 4
        assert '25' in service['modifiers']
        assert '59' in service['modifiers']
