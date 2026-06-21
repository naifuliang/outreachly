"""P1: ICP validation (field-level errors) and persistence."""

import icp


VALID = {
    "product": "Appointment SaaS for dental clinics",
    "industries": ["dental", "healthcare"],
    "titles": ["practice owner", "office manager"],
    "keywords": ["dental clinic", "dentist"],
    "geographies": ["Austin, TX"],
    "channels": ["email"],
    "language": "en",
}


def test_template_is_valid():
    # The blank template intentionally has empty required arrays, so it is INVALID until filled.
    errors = icp.validate(icp.TEMPLATE)
    assert any("industries" in e or "titles" in e or "keywords" in e for e in errors)


def test_valid_icp_passes():
    assert icp.validate(VALID) == []


def test_missing_required_field_is_named():
    bad = {k: v for k, v in VALID.items() if k != "industries"}
    errors = icp.validate(bad)
    assert errors
    assert any("industries" in e for e in errors)


def test_wrong_type_is_rejected():
    bad = {**VALID, "industries": "dental"}  # should be an array
    errors = icp.validate(bad)
    assert any("industries" in e for e in errors)


def test_unknown_field_rejected():
    bad = {**VALID, "budget": 1000}  # additionalProperties: false
    errors = icp.validate(bad)
    assert errors


def test_save_and_load_roundtrip(tmp_path):
    p = tmp_path / "icp.json"
    assert icp.save_icp(VALID, p) == []
    assert icp.load_icp(p) == VALID


def test_save_rejects_invalid(tmp_path):
    p = tmp_path / "icp.json"
    bad = {**VALID, "industries": []}  # minItems: 1
    errors = icp.save_icp(bad, p)
    assert errors
    assert not p.exists()  # not written when invalid
