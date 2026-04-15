"""
Parse BEDA_Enriched.xlsx and return a dict of
{category: {indicator: {current_value, prior_value, yoy_change}}}
"""
from pathlib import Path
import re
import openpyxl

# Resolve the Excel file relative to this package, or fall back to project root
_HERE = Path(__file__).resolve().parent
# data/baseline/ -> data/ -> project root; Excel sits in data/
_DEFAULT_PATH = _HERE.parent / "BEDA_Enriched.xlsx"


_UNICODE_DASHES = str.maketrans({
    "\u2014": "-",  # em dash
    "\u2013": "-",  # en dash
    "\u2012": "-",  # figure dash
    "\u2010": "-",  # hyphen
    "\u2011": "-",  # non-breaking hyphen
})


def _normalize(s: str) -> str:
    """Normalise Unicode dashes and tidy whitespace in a string."""
    return s.translate(_UNICODE_DASHES).strip()


def _clean(val):
    """Convert a raw cell value to a clean string or float where possible."""
    if val is None:
        return None
    s = _normalize(str(val))
    # Strip leading tildes and common currency/unit prefixes for numeric parse
    numeric_s = re.sub(r"[~A$,m%cpl\s]", "", s)
    try:
        return float(numeric_s)
    except ValueError:
        return s


def load_baseline(excel_path: str | Path | None = None) -> dict:
    """
    Returns:
        {
            "Aviation & Connectivity": {
                "Jet fuel price - Singapore Kerosene (USD/bbl)": {
                    "current_value": 83.4,
                    "prior_value": 96.2,
                    "yoy_change": "-13.3%",
                    "reference_period": "Mar 2026",
                },
                ...
            },
            ...
        }
    """
    path = Path(excel_path) if excel_path else _DEFAULT_PATH
    if not path.exists():
        raise FileNotFoundError(f"BEDA_Enriched.xlsx not found at {path}")

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Full Data"]

    result: dict = {}
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # header
        category, indicator, _geo, current, ref_period, prior, _prior_period, yoy = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
        )
        if category is None or indicator is None:
            continue

        cat = _normalize(str(category))
        ind = _normalize(str(indicator))
        result.setdefault(cat, {})[ind] = {
            "current_value": _clean(current),
            "prior_value": _clean(prior),
            "yoy_change": str(yoy).strip() if yoy is not None else None,
            "reference_period": str(ref_period).strip() if ref_period is not None else None,
        }

    wb.close()
    return result


if __name__ == "__main__":
    import json

    data = load_baseline()
    for cat, indicators in data.items():
        print(f"\n{cat} ({len(indicators)} indicators)")
        for ind, vals in list(indicators.items())[:2]:
            print(f"  {ind}: {vals}")
