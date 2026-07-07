import pytest
from app.services.validator import validate_and_derive
from app.schemas import ItemCategory, JobStatus

def test_validate_and_derive_empty():
    res = validate_and_derive({}, "test_job")
    assert res.job_id == "test_job"
    assert res.status == JobStatus.COMPLETED
    assert res.summary is not None
    assert res.summary.total_pipe_length_m == 0

def test_validate_and_derive_gasket_bolt_derivation():
    raw_data = {
        "items": [
            {
                "category": "FLANGE",
                "description": "Weld Neck Flange",
                "size_nps": '6"',
                "quantity": 2
            },
            {
                "category": "VALVE",
                "description": "Flanged Gate Valve",
                "size_nps": '6"',
                "end_type": "FLGD",
                "quantity": 1
            }
        ]
    }
    # Total flanges = 2, Flanged valves = 1 => Total joints = 3
    # Gaskets derived = 3, Bolt sets derived = 3
    res = validate_and_derive(raw_data, "job_123")
    
    assert res.summary.flanges == 2
    assert res.summary.valves == 1
    assert res.summary.gaskets == 3
    assert res.summary.bolt_sets == 3
    
    # Check the derived items
    gaskets = [i for i in res.items if i.category == ItemCategory.GASKET]
    bolts = [i for i in res.items if i.category == ItemCategory.BOLT]
    
    assert len(gaskets) == 1
    assert gaskets[0].quantity == 3
    assert "Derived programmatically" in gaskets[0].remarks
    
    assert len(bolts) == 1
    assert bolts[0].quantity == 3
    assert "Derived programmatically" in bolts[0].remarks

def test_validate_and_derive_nps_normalization():
    raw_data = {
        "items": [
            {
                "category": "PIPE",
                "size_nps": "6", # missing quotes
                "quantity": 10
            },
            {
                "category": "FITTING",
                "size_nps": "6x4", # missing quotes
                "quantity": 2
            }
        ]
    }
    res = validate_and_derive(raw_data, "job_123")
    assert res.items[0].size_nps == '6"'
    assert res.items[1].size_nps == '6"x4"'

def test_qa_warning_on_pipe_length_mismatch():
    raw_data = {
        "summary": {
            "total_pipe_length_m": 100.0
        },
        "items": [
            {
                "category": "PIPE",
                "quantity": 50.0 # Will be used as length_m. 50 != 100, > 5% diff
            }
        ]
    }
    res = validate_and_derive(raw_data, "job_123")
    
    pipe = res.items[0]
    assert pipe.length_m == 50.0
    assert "QA warning" in pipe.remarks
