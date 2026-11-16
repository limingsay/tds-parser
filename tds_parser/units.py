"""Unit normalisation helpers."""

# units we recognise as "this number is a measured property value"
UNITS = [
    "g/10min", "g/10 min", "g/10min.", "g/cm3", "g/cm³", "kg/m3", "kg/m³",
    "MPa", "kPa", "GPa", "N/mm2", "N/mm²", "kJ/m2", "kJ/m²", "KJ/m2", "J/m",
    "°C", "℃", "C", "%", "mm/min", "mm/s", "um", "µm", "mm", "mg", "kg", "g",
    "sec", "s", "min", "h", "dB", "Ω", "ohm", "MPa·m1/2", "kPa·m1/2",
]

_CANON = {
    "g/cm3": "g/cm³", "kg/m3": "kg/m³", "N/mm2": "N/mm²",
    "g/10 min": "g/10min", "g/10  min": "g/10min",
    "kJ/m2": "kJ/m²", "KJ/m2": "kJ/m²", "℃": "°C", "um": "µm",
}


def canon_unit(unit):
    """Return a canonical spelling for a unit, or the input when unknown."""
    u = (unit or "").strip()
    key = u.replace(" ", "").lower()
    return _CANON.get(u, _CANON.get(key, u))
