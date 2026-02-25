from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Norm:
    enbez: str = ""
    titel: str = ""
    text_content: str = ""
    gliederung_kennzahl: str = ""
    gliederung_bez: str = ""
    gliederung_titel: str = ""
    sort_order: int = 0


@dataclass
class ParsedLaw:
    jurabk: str
    full_title: str
    slug: str
    enactment_date: str = ""
    norms: list[Norm] = field(default_factory=list)


@dataclass
class LawEntry:
    slug: str
    title: str
    url: str
