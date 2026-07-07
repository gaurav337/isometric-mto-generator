import pytest
from app.schemas import MTOItem, ItemCategory, ItemUnit

def test_mto_item_pipe_validation():
    item = MTOItem(
        item_no=1,
        category=ItemCategory.PIPE,
        description="Seamless Pipe",
        size_nps='6"',
        quantity=12.5,
        unit=ItemUnit.M,
        remarks=""
    )
    assert item.length_m == 12.5
    assert item.unit == ItemUnit.M

def test_mto_item_pipe_missing_quantity_or_length():
    with pytest.raises(ValueError):
        MTOItem(
            item_no=1,
            category=ItemCategory.PIPE,
            description="Seamless Pipe",
            size_nps='6"',
            quantity=0,
            unit=ItemUnit.M,
            remarks=""
        )

def test_size_nps_validation_valid():
    # Valid formats
    for size in ['6"', '6"x4"', '1.5"', '1/2"']:
        item = MTOItem(
            item_no=1,
            category=ItemCategory.FITTING,
            description="Elbow",
            size_nps=size,
            quantity=1,
            unit=ItemUnit.EA,
            remarks=""
        )
        assert item.size_nps == size

def test_size_nps_validation_invalid_missing_quotes():
    # Should raise error if no quotes
    with pytest.raises(ValueError, match="NPS size must contain double quotes"):
        MTOItem(
            item_no=1,
            category=ItemCategory.FITTING,
            description="Elbow",
            size_nps="6",
            quantity=1,
            unit=ItemUnit.EA,
            remarks=""
        )

def test_mto_item_bolt_unit():
    item = MTOItem(
        item_no=1,
        category=ItemCategory.BOLT,
        description="Stud Bolts",
        size_nps='5/8"',
        quantity=4,
        unit=ItemUnit.EA, # Even if provided as EA, should be forced to SET by validator
        remarks=""
    )
    assert item.unit == ItemUnit.SET
