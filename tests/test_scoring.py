"""P2: ICP-match scoring distinguishes matches; status state machine rejects illegal moves."""

import pytest

import crm


ICP = {
    "industries": ["dental"],
    "titles": ["practice owner"],
    "keywords": ["dental clinic", "dentist"],
    "geographies": ["Austin"],
}


def test_high_match_scores_higher_than_mismatch():
    high = {
        "name": "Bright Smile Dental Clinic",
        "company": "Bright Smile Dental",
        "title": "Practice Owner",
        "location": "Austin, TX",
        "profile": "family dentist in austin",
    }
    low = {
        "name": "Joe's Auto Repair",
        "company": "Joe Auto",
        "title": "Mechanic",
        "location": "Detroit, MI",
        "profile": "car repair shop",
    }
    s_high = crm.score_lead(high, ICP)
    s_low = crm.score_lead(low, ICP)
    assert s_high >= 70
    assert s_low <= 20
    assert s_high > s_low


def test_no_geographies_does_not_penalize():
    icp = {**ICP, "geographies": []}
    lead = {"name": "Dental clinic", "title": "practice owner", "profile": "dentist"}
    assert crm.score_lead(lead, icp) >= 70


def test_legal_transition(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "maps", "name": "Acme"}, db)
    assert crm.set_status(lid, "contacted", db) == "contacted"
    assert crm.set_status(lid, "replied", db) == "replied"
    assert crm.set_status(lid, "converted", db) == "converted"


def test_illegal_transition_rejected(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "maps", "name": "Acme"}, db)
    # new → converted is illegal (no outreach yet)
    with pytest.raises(crm.IllegalTransition):
        crm.set_status(lid, "converted", db)


def test_terminal_state_has_no_exits(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "maps", "name": "Acme"}, db)
    crm.set_status(lid, "rejected", db)
    with pytest.raises(crm.IllegalTransition):
        crm.set_status(lid, "contacted", db)


def test_rescore_all_updates_scores(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    crm.upsert_lead({"source": "maps", "name": "Bright Dental Clinic", "title": "practice owner",
                     "location": "Austin"}, db)
    n = crm.rescore_all(ICP, db)
    assert n == 1
    assert crm.list_leads(path=db)[0]["score"] >= 70
