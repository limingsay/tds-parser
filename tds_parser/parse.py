"""Parse TDS plain text into structured property rows.

The parser is deliberately dependency free: PDF extraction lives in
``tds_parser.extract`` and is optional, everything here works on plain text.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, asdict
from typing import Iterable, List, Optional

from .units import UNITS, canon_unit

# --------------------------------------------------------------------------
# property aliases: canonical key -> spelling variants (zh + en)
# --------------------------------------------------------------------------
ALIASES = {
    "density": ["density", "specific gravity", "比重", "密度"],
    "mfr": [
        "melt flow rate", "melt flow index", "melt mass-flow rate", "mfr", "mfi",
        "melt volume rate", "mvr", "熔体流动速率", "熔融指数", "熔指数", "熔指", "流动性",
    ],
    "tensile_strength": [
        "tensile strength", "tensile stress", "拉伸强度", "抗拉强度", "断裂拉伸强度",
        "yield tensile strength", "tensile stress at yield", "tensile stress at break",
    ],
    "tensile_modulus": ["tensile modulus", "young's modulus", "拉伸模量", "杨氏模量"],
    "elongation": ["elongation at break", "elongation", "断裂伸长率", "伸长率", "断裂伸长"],
    "flexural_modulus": ["flexural modulus", "弯曲模量", "挠曲模量"],
    "flexural_strength": ["flexural strength", "弯曲强度", "挠曲强度"],
    "izod_notched": [
        "izod notched", "charpy notched", "notched izod", "notched impact",
        "impact strength", "悬臂梁缺口冲击", "简支梁缺口冲击", "缺口冲击强度", "冲击强度",
    ],
    "hdT": [
        "heat deflection temperature", "heat distortion temperature", "hdt",
        "热变形温度", "热变形",
    ],
    "vicat": ["vicat softening", "vicat", "维卡软化点", "维卡软化", "维卡"],
    "water_absorption": ["water absorption", "吸水率", "吸湿率"],
    "hardness": ["shore hardness", "shore d", "shore a", "hardness", "硬度", "邵氏硬度", "邵氏"],
    "melting_point": ["melting point", "melting temperature", "melting", "熔点", "熔融温度"],
    "processing_temp": [
        "processing temperature", "melt temperature", "barrel temperature",
        "加工温度", "熔体温度", "料筒温度", "成型温度",
    ],
    "mold_temp": ["mold temperature", "tool temperature", "模具温度", "模温"],
    "drying": ["drying", "dryer", "干燥条件", "干燥"],
    "molding_shrinkage": ["molding shrinkage", "shrinkage", "成型收缩率", "收缩率"],
    "glass_transition": ["glass transition", "tg", "玻璃化转变温度", "玻璃化温度"],
    "flame_rating": ["flame rating", "flame retardant rating", "ul 94", "ul94", "阻燃等级", "阻燃级别"],
    "dielectric_strength": ["dielectric strength", "击穿强度", "介电强度"],
    "surface_resistivity": ["surface resistivity", "表面电阻率", "表面电阻"],
    "volume_resistivity": ["volume resistivity", "体积电阻率", "体积电阻"],
    "thermal_conductivity": ["thermal conductivity", "导热系数", "热导率"],
    "cte": ["coefficient of linear thermal expansion", "clte", "cte", "线膨胀系数"],
}

# longest alias first so "tensile strength" wins over "tensile"
_ALIAS_CHECKS = sorted(
    ((alias, key) for key, names in ALIASES.items() for alias in names),
    key=lambda pair: len(pair[0]),
    reverse=True,
)

_NUM = r"[<>≤≥]?\s*\d+(?:[.,]\d+)?(?:\s*[~\-–]\s*\d+(?:[.,]\d+)?)?"
_UNIT_RE = "|".join(re.escape(u) for u in sorted(UNITS, key=len, reverse=True))
_METHOD_RE = re.compile(
    r"(?:ASTM|ISO|GB/T|GB|JIS|DIN|IEC|UL)\s*[A-Za-z]?\s*\d+(?:[A-Za-z0-9\-./ ]*)",
    re.I,
)
_VALUE_RE = re.compile(
    r"(?P<value>" + _NUM + r")\s*(?P<unit>" + _UNIT_RE + r")(?![A-Za-z0-9])"
)
_FLAME_RE = re.compile(
    r"(?:UL\s*94|阻燃)\s*[:：]?\s*(?P<grade>V-?[0-2]|5V[AB]|HB|V0|V1|V2)", re.I
)
_NOISE = re.compile(
    r"(technical\s+data\s+sheet|data\s+sheet|page\s+\d+\s*(?:of|/)\s*\d+|"
    r"技术数据表|物性表|产品信息|第\s*\d+\s*页|\d{4}[-/]\d{1,2}[-/]\d{1,2}|"
    r"^\s*(?:www\.|https?://)|版权所有|copyright)",
    re.I,
)


def _clean(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[|│┃]+", " ", s)
    s = re.sub(r"[\s\u3000]+", " ", s)
    return s.strip(" \t:-—·•,;：")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def normalize_name(name: str) -> Optional[str]:
    """Map a raw property label to a canonical key (or ``None``)."""
    raw = _clean(name)
    if not raw:
        return None
    probe = _slug(raw)
    probe_zh = re.sub(r"\s+", "", raw)
    for alias, key in _ALIAS_CHECKS:
        if _slug(alias) and _slug(alias) in probe:
            return key
        if re.search(r"[\u4e00-\u9fff]", alias) and alias in probe_zh:
            return key
    return None


def _to_number(raw: str) -> Optional[float]:
    nums = re.findall(r"\d+(?:[.,]\d+)?", raw)
    if not nums:
        return None
    try:
        return float(nums[0].replace(",", "").replace(" ", ""))
    except ValueError:
        return None


@dataclass
class Property:
    """A single measured property found in a TDS."""

    name: str
    key: Optional[str]
    value: Optional[float]
    raw_value: str
    unit: str
    method: Optional[str]
    source_line: str

    def as_dict(self) -> dict:
        return asdict(self)


def parse_line(line: str) -> Optional[Property]:
    """Parse one text line into a :class:`Property`, or return ``None``."""
    text = _clean(line)
    if len(text) < 6 or _NOISE.search(text):
        return None

    # 1) flame rating needs its own pattern (no numeric unit)
    flame = _FLAME_RE.search(text)
    if flame:
        name = _clean(text[: flame.start()]) or "UL 94"
        return Property(
            name=name,
            key="flame_rating",
            value=None,
            raw_value=flame.group("grade").upper().replace("V0", "V-0"),
            unit="",
            method="UL 94" if "ul" in text.lower() else None,
            source_line=text,
        )

    # 2) value + unit, prefer the match closest to a known method marker
    match = None
    for candidate in _VALUE_RE.finditer(text):
        if match is None:
            match = candidate
        if _METHOD_RE.search(text[candidate.end():]):
            match = candidate
            break
    if match is None:
        return None

    name = _clean(text[: match.start()])
    rest = text[match.end():]
    method_match = _METHOD_RE.search(rest)
    method = _clean(method_match.group(0)) if method_match else None
    unit = canon_unit(match.group("unit"))

    if not name or len(name) < 2:
        # value-first layouts ("1.05 g/cm3  Density"): fall back to trailing text
        name = _clean(text[match.end():])
        if not name:
            return None

    return Property(
        name=name,
        key=normalize_name(name),
        value=_to_number(match.group("value")),
        raw_value=_clean(match.group("value")),
        unit=unit,
        method=method,
        source_line=text,
    )


def parse_text(text: str) -> List[Property]:
    """Parse a whole TDS text dump into properties (order preserved)."""
    out: List[Property] = []
    for line in text.splitlines():
        prop = parse_line(line)
        if prop is not None:
            out.append(prop)
    return out


def keyed(props: Iterable[Property]) -> dict:
    """Collapse a property list into ``{key: {...}}`` keeping the first hit."""
    result = {}
    for prop in props:
        if not prop.key or prop.key in result:
            continue
        result[prop.key] = {
            "value": prop.value,
            "raw_value": prop.raw_value,
            "unit": prop.unit,
            "method": prop.method,
        }
    return result


# --------------------------------------------------------------------------
# serialisers
# --------------------------------------------------------------------------
def to_markdown(props: Iterable[Property]) -> str:
    rows = list(props)
    head = "| 属性 | 数值 | 单位 | 测试方法 |\n|---|---|---|---|\n"
    body = "".join(
        f"| {p.name} | {p.raw_value} | {p.unit} | {p.method or ''} |\n" for p in rows
    )
    return head + body if rows else ""


def to_csv(props: Iterable[Property]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["name", "key", "value", "raw_value", "unit", "method"])
    for p in props:
        writer.writerow([p.name, p.key or "", p.value if p.value is not None else "",
                         p.raw_value, p.unit, p.method or ""])
    return buf.getvalue()


def to_json(props: Iterable[Property], source: str = "", pages: int = 0) -> str:
    rows = list(props)
    payload = {
        "source": source,
        "pages": pages,
        "property_count": len(rows),
        "matched_count": sum(1 for p in rows if p.key),
        "properties": [p.as_dict() for p in rows],
        "normalized": keyed(rows),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
