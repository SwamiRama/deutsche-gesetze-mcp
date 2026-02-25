from __future__ import annotations

from deutsche_gesetze_mcp.db import Database, _sanitize_fts_query


def test_list_laws(populated_db: Database) -> None:
    laws = populated_db.list_laws()
    assert len(laws) == 2
    jurabks = {law["jurabk"] for law in laws}
    assert jurabks == {"BGB", "GG"}


def test_list_laws_filter(populated_db: Database) -> None:
    laws = populated_db.list_laws(filter_text="Bürger")
    assert len(laws) == 1
    assert laws[0]["jurabk"] == "BGB"


def test_list_laws_filter_abbreviation(populated_db: Database) -> None:
    laws = populated_db.list_laws(filter_text="GG")
    assert len(laws) == 1
    assert laws[0]["jurabk"] == "GG"


def test_get_paragraph(populated_db: Database) -> None:
    result = populated_db.get_paragraph("BGB", "§ 823")
    assert result is not None
    assert result["titel"] == "Schadensersatzpflicht"
    assert "vorsätzlich" in result["text_content"]


def test_get_paragraph_not_found(populated_db: Database) -> None:
    result = populated_db.get_paragraph("BGB", "§ 9999")
    assert result is None


def test_get_paragraphs_range(populated_db: Database) -> None:
    results = populated_db.get_paragraphs_range("BGB", "§ 1", "§ 3")
    assert len(results) == 3
    assert results[0]["enbez"] == "§ 1"
    assert results[2]["enbez"] == "§ 3"


def test_get_paragraphs_range_not_found(populated_db: Database) -> None:
    results = populated_db.get_paragraphs_range("BGB", "§ 9998", "§ 9999")
    assert results == []


def test_get_law_structure(populated_db: Database) -> None:
    structure = populated_db.get_law_structure("BGB")
    assert len(structure) == 5
    assert structure[0]["enbez"] == "§ 1"


def test_get_law_structure_not_found(populated_db: Database) -> None:
    structure = populated_db.get_law_structure("NONEXISTENT")
    assert structure == []


def test_search(populated_db: Database) -> None:
    results = populated_db.search("Rechtsfähigkeit")
    assert len(results) >= 1
    assert results[0]["jurabk"] == "BGB"
    assert results[0]["enbez"] == "§ 1"


def test_search_with_law_filter(populated_db: Database) -> None:
    results = populated_db.search("Recht", laws=["GG"])
    assert all(r["jurabk"] == "GG" for r in results)


def test_search_no_results(populated_db: Database) -> None:
    results = populated_db.search("Quantencomputer")
    assert results == []


def test_get_law_metadata(populated_db: Database) -> None:
    meta = populated_db.get_law_metadata("BGB")
    assert meta is not None
    assert meta["full_title"] == "Bürgerliches Gesetzbuch"
    assert meta["norm_count"] == 5


def test_get_law_metadata_not_found(populated_db: Database) -> None:
    meta = populated_db.get_law_metadata("NONEXISTENT")
    assert meta is None


def test_get_stats(populated_db: Database) -> None:
    stats = populated_db.get_stats()
    assert stats["law_count"] == 2
    assert stats["norm_count"] == 7  # 5 BGB + 2 GG


def test_upsert_updates_existing(populated_db: Database, sample_bgb_path) -> None:
    from deutsche_gesetze_mcp.parser import parse_law_xml

    law = parse_law_xml(sample_bgb_path, "bgb")
    law.full_title = "Updated Title"
    populated_db.upsert_law(law)

    meta = populated_db.get_law_metadata("BGB")
    assert meta is not None
    assert meta["full_title"] == "Updated Title"

    laws = populated_db.list_laws()
    assert len(laws) == 2  # still 2, not 3


def test_sanitize_fts_query() -> None:
    assert _sanitize_fts_query("hello world") == '"hello" "world"'
    assert _sanitize_fts_query("§ 823") == '"823"'
    assert _sanitize_fts_query("Kündigung") == '"Kündigung"'
    assert _sanitize_fts_query("") == ""
    assert _sanitize_fts_query("OR AND NOT") == '"OR" "AND" "NOT"'
