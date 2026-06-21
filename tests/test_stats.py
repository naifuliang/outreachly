"""P6: crm.stats funnel counts."""

import crm


def test_stats_counts(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    a, _ = crm.upsert_lead({"source": "linkedin", "external_id": "u1", "name": "A"}, db)
    crm.upsert_lead({"source": "twitter", "external_id": "x1", "name": "B"}, db)
    crm.mark_contacted(a, db)
    crm.log_message(a, "linkedin", "outbound", "hi", path=db)

    s = crm.stats(db)
    assert s["total_leads"] == 2
    assert s["total_messages"] == 1
    assert s["by_status"]["contacted"] == 1
    assert s["by_status"]["new"] == 1
    assert s["by_source"] == {"linkedin": 1, "twitter": 1}
