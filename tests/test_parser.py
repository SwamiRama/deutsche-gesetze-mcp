from __future__ import annotations

from pathlib import Path

from deutsche_gesetze_mcp.parser import parse_law_xml


def test_parse_bgb_header(sample_bgb_path: Path) -> None:
    law = parse_law_xml(sample_bgb_path, "bgb")
    assert law.jurabk == "BGB"
    assert law.full_title == "Bürgerliches Gesetzbuch"
    assert law.slug == "bgb"
    assert law.enactment_date == "1896-08-18"


def test_parse_bgb_norms(sample_bgb_path: Path) -> None:
    law = parse_law_xml(sample_bgb_path, "bgb")
    assert len(law.norms) == 5

    p1 = law.norms[0]
    assert p1.enbez == "§ 1"
    assert p1.titel == "Beginn der Rechtsfähigkeit"
    assert "Rechtsfähigkeit des Menschen" in p1.text_content
    assert p1.gliederung_bez == "Buch 1"
    assert p1.gliederung_titel == "Allgemeiner Teil"
    assert p1.sort_order == 1


def test_parse_bgb_paragraph_823(sample_bgb_path: Path) -> None:
    law = parse_law_xml(sample_bgb_path, "bgb")
    p823 = next(n for n in law.norms if n.enbez == "§ 823")
    assert p823.titel == "Schadensersatzpflicht"
    assert "vorsätzlich oder fahrlässig" in p823.text_content
    assert "(2)" in p823.text_content


def test_parse_gg(sample_gg_path: Path) -> None:
    law = parse_law_xml(sample_gg_path, "gg")
    assert law.jurabk == "GG"
    assert law.full_title == "Grundgesetz für die Bundesrepublik Deutschland"
    assert len(law.norms) == 2

    art1 = law.norms[0]
    assert art1.enbez == "Art 1"
    assert "Würde des Menschen" in art1.text_content
    assert art1.gliederung_bez == "I."
    assert art1.gliederung_titel == "Die Grundrechte"


def test_parse_empty_xml(tmp_path: Path) -> None:
    xml = tmp_path / "empty.xml"
    xml.write_text('<?xml version="1.0"?><dokumente></dokumente>')
    law = parse_law_xml(xml, "empty")
    assert law.jurabk == ""
    assert law.norms == []
