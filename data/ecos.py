# data/ecos.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple, Any, Dict

import pandas as pd
import requests

ECOS_BASE = "https://ecos.bok.or.kr/api/StatisticSearch"

# 너가 확정한 지표 코드
INDICATORS: dict[str, dict[str, str]] = {
    "한국은행 기준금리": {"stat_code": "722Y001", "cycle": "M", "item_code1": "0101000"},
    "원/달러 환율": {"stat_code": "731Y001", "cycle": "D", "item_code1": "0000001"},
    "경제성장률": {"stat_code": "902Y015", "cycle": "Q", "item_code1": "KOR"},
    "실업률": {"stat_code": "901Y027", "cycle": "M", "item_code1": "I61BC"},
    "소비자물가상승률" : {"stat_code": "901Y009", "cycle": "M", "item_code1": "0"},
}

@dataclass(frozen=True)
class KpiValue:
    name: str
    latest: Optional[float]
    prev: Optional[float]
    unit: Optional[str]
    latest_date: Optional[str]
    prev_date: Optional[str]

def default_period_by_cycle(cycle: str) -> Tuple[str, str]:
    today = datetime.today()

    if cycle == "D":
        end = today.strftime("%Y%m%d")
        start = (today - timedelta(days=45)).strftime("%Y%m%d")
    elif cycle == "M":
        end = today.strftime("%Y%m")
        start = today.replace(year=today.year - 2).strftime("%Y%m")
    elif cycle == "Q":
        year = today.year
        q = (today.month - 1) // 3 + 1
        end = f"{year}Q{q}"
        start = f"{year - 6}Q1"
    else:  # "A"
        end = str(today.year)
        start = str(today.year - 15)

    return start, end

def build_ecos_url(
    api_key: str,
    stat_code: str,
    cycle: str,
    start: str,
    end: str,
    item_code1: str = "",
    item_code2: str = "",
    lang: str = "kr",
    max_rows: int = 2000,
) -> str:
    return (
        f"{ECOS_BASE}/"
        f"{api_key}/json/{lang}/1/{max_rows}/"
        f"{stat_code}/{cycle}/{start}/{end}/"
        f"{item_code1}/{item_code2}"
    )

def _rows_to_df(json_obj: Dict[str, Any]) -> pd.DataFrame:
    block = json_obj.get("StatisticSearch", {})
    rows = block.get("row", []) if isinstance(block, dict) else []
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    date_col = next((c for c in ("TIME", "DATE", "TIME_PERIOD") if c in df.columns), None)
    value_col = next((c for c in ("DATA_VALUE", "VALUE") if c in df.columns), None)
    if not date_col or not value_col:
        return pd.DataFrame()

    out = df.rename(columns={date_col: "date", value_col: "value"}).copy()
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna(subset=["date", "value"]).sort_values("date")
    return out

def fetch_kpi_value(
    api_key: str,
    name: str,
    stat_code: str,
    cycle: str,
    item_code1: str = "",
    item_code2: str = "",
    start: Optional[str] = None,
    end: Optional[str] = None,
    timeout_sec: int = 20,
) -> KpiValue:
    if not start or not end:
        start, end = default_period_by_cycle(cycle)

    url = build_ecos_url(
        api_key=api_key,
        stat_code=stat_code,
        cycle=cycle,
        start=start,
        end=end,
        item_code1=item_code1,
        item_code2=item_code2,
    )

    try:
        r = requests.get(url, timeout=timeout_sec)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return KpiValue(name, None, None, None, None, None)

    raw = _rows_to_df(data)
    if raw.empty:
        return KpiValue(name, None, None, None, None, None)

    series = _normalize(raw)
    if series.empty:
        return KpiValue(name, None, None, None, None, None)

    unit_col = next((c for c in ("UNIT_NAME", "UNIT") if c in raw.columns), None)
    unit = str(raw[unit_col].iloc[-1]) if unit_col else None

    latest = float(series["value"].iloc[-1])
    latest_date = str(series["date"].iloc[-1])

    prev = float(series["value"].iloc[-2]) if len(series) >= 2 else None
    prev_date = str(series["date"].iloc[-2]) if len(series) >= 2 else None

    return KpiValue(name, latest, prev, unit, latest_date, prev_date)

def fetch_all_kpis(api_key: str) -> list[KpiValue]:
    out: list[KpiValue] = []
    for name, cfg in INDICATORS.items():
        out.append(
            fetch_kpi_value(
                api_key=api_key,
                name=name,
                stat_code=cfg["stat_code"],
                cycle=cfg["cycle"],
                item_code1=cfg.get("item_code1", ""),
                item_code2=cfg.get("item_code2", ""),
            )
        )
    return out
