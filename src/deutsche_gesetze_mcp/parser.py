from __future__ import annotations

from pathlib import Path

from lxml import etree

from deutsche_gesetze_mcp.models import Norm, ParsedLaw


def _text_of(element: etree._Element | None) -> str:
    if element is None:
        return ""
    return (element.text or "").strip()


def _extract_text(element: etree._Element) -> str:
    parts: list[str] = []

    for child in element.iter():
        tag = etree.QName(child.tag).localname if isinstance(child.tag, str) else ""

        if tag == "P":
            text = child.text or ""
            for sub in child:
                sub_tag = etree.QName(sub.tag).localname if isinstance(sub.tag, str) else ""
                if sub_tag == "BR":
                    text += "\n"
                text += sub.text or ""
                text += sub.tail or ""
            text = text.strip()
            if text:
                parts.append(text)

        elif tag == "DL":
            for dt_or_dd in child:
                dt_dd_tag = etree.QName(dt_or_dd.tag).localname if isinstance(dt_or_dd.tag, str) else ""
                inner = dt_or_dd.text or ""
                for sub in dt_or_dd:
                    inner += sub.text or ""
                    inner += sub.tail or ""
                inner = inner.strip()
                if dt_dd_tag == "DT" and inner:
                    parts.append(inner)
                elif dt_dd_tag == "DD" and inner:
                    parts.append(f"  {inner}")

        elif tag == "table":
            for row in child.iter():
                row_tag = etree.QName(row.tag).localname if isinstance(row.tag, str) else ""
                if row_tag == "entry":
                    cell_text = "".join(row.itertext()).strip()
                    if cell_text:
                        parts.append(cell_text)

    return "\n".join(parts)


def parse_law_xml(xml_path: Path, slug: str) -> ParsedLaw:
    tree = etree.parse(str(xml_path))  # noqa: S320
    root = tree.getroot()

    norms = root.findall(".//norm")
    if not norms:
        return ParsedLaw(jurabk="", full_title="", slug=slug)

    header = norms[0]
    meta = header.find(".//metadaten")
    jurabk = _text_of(meta.find("jurabk")) if meta is not None else ""
    full_title = ""
    enactment_date = ""

    if meta is not None:
        langue = meta.find("langue")
        if langue is not None:
            full_title = (langue.text or "").strip()

        ausfertigung = meta.find("ausfertigung-datum")
        if ausfertigung is not None:
            enactment_date = ausfertigung.get("manuell", "") or (ausfertigung.text or "").strip()

    parsed_norms: list[Norm] = []

    for idx, norm_el in enumerate(norms[1:], start=1):
        norm_meta = norm_el.find(".//metadaten")
        if norm_meta is None:
            continue

        enbez = _text_of(norm_meta.find("enbez"))
        titel = _text_of(norm_meta.find("titel"))

        gl_kennzahl = ""
        gl_bez = ""
        gl_titel = ""
        gliederung = norm_meta.find("gliederungseinheit")
        if gliederung is not None:
            gl_kennzahl = _text_of(gliederung.find("gliederungskennzahl"))
            gl_bez = _text_of(gliederung.find("gliederungsbez"))
            gl_titel = _text_of(gliederung.find("gliederungstitel"))

        text_content = ""
        textdaten = norm_el.find(".//textdaten")
        if textdaten is not None:
            content_el = textdaten.find(".//Content")
            if content_el is not None:
                text_content = _extract_text(content_el)

        parsed_norms.append(
            Norm(
                enbez=enbez,
                titel=titel,
                text_content=text_content,
                gliederung_kennzahl=gl_kennzahl,
                gliederung_bez=gl_bez,
                gliederung_titel=gl_titel,
                sort_order=idx,
            )
        )

    return ParsedLaw(
        jurabk=jurabk,
        full_title=full_title,
        slug=slug,
        enactment_date=enactment_date,
        norms=parsed_norms,
    )
