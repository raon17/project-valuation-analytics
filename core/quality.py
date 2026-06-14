import pandas as pd
import numpy as np

# ── helpers ──────────────────────────────────────────────────────────────────

def _cagr(series: pd.Series) -> float:
    """
    series: 시간순 정렬된 연간 값 (오래된 것 → 최근 것)
    CAGR = (end / start) ^ (1 / n_years) - 1
    """
    series = series.dropna()
    if len(series) < 2:
        return np.nan
    start, end = series.iloc[0], series.iloc[-1]
    if start <= 0 or end <= 0:
        return np.nan
    n = len(series) - 1
    return (end / start) ** (1 / n) - 1


def _safe_get(info: dict, *keys, default=np.nan):
    for k in keys:
        v = info.get(k)
        if v is not None:
            return v
    return default


def _row(df: pd.DataFrame, *labels):
    """DataFrame에서 label 매칭되는 row 반환. 컬럼은 최근→과거 순."""
    for label in labels:
        matches = [i for i in df.index if label.lower() in str(i).lower()]
        if matches:
            return df.loc[matches[0]]
    return None


# ── main ─────────────────────────────────────────────────────────────────────

def run_quality(data: dict) -> dict:
    info      = data["info"]
    fin       = data["financials"]   # columns: 최근→과거 (left→right)
    bal       = data["balance"]
    cf        = data["cashflow"]

    results = {}

    # 1. Revenue CAGR (5Y)
    rev_row = _row(fin, "Total Revenue")
    if rev_row is not None:
        rev_series = rev_row[::-1].astype(float)   # 과거→최근 정렬
        results["revenue_cagr"] = _cagr(rev_series)
    else:
        results["revenue_cagr"] = np.nan

    # 2. EPS CAGR (5Y) — yfinance info에서 trailing/forward EPS 직접 없음
    #    Net Income 기반으로 대리 계산
    ni_row = _row(fin, "Net Income")
    if ni_row is not None:
        ni_series = ni_row[::-1].astype(float)
        results["ni_cagr"] = _cagr(ni_series)
    else:
        results["ni_cagr"] = np.nan

    # 3. FCF = Operating Cash Flow - CapEx
    ocf_row  = _row(cf, "Operating Cash Flow", "Total Cash From Operating")
    capex_row = _row(cf, "Capital Expenditure", "Capital Expenditures")

    if ocf_row is not None and capex_row is not None:
        ocf   = ocf_row[::-1].astype(float)
        capex = capex_row[::-1].astype(float).abs()
        fcf   = ocf - capex
        results["fcf_series"]  = fcf.tolist()        # valuation.py에서 재사용
        results["fcf_latest"]  = fcf.iloc[-1]
        results["fcf_cagr"]    = _cagr(fcf.clip(lower=0.01))  # 음수 CAGR 방어
    else:
        results["fcf_series"]  = []
        results["fcf_latest"]  = np.nan
        results["fcf_cagr"]    = np.nan

    # 4. Gross Margin = Gross Profit / Revenue (최근 연도)
    gp_row  = _row(fin, "Gross Profit")
    rev_latest = rev_row.iloc[0] if rev_row is not None else np.nan
    gp_latest  = gp_row.iloc[0]  if gp_row  is not None else np.nan
    results["gross_margin"] = (gp_latest / rev_latest) if rev_latest else np.nan

    # 5. Net Margin = Net Income / Revenue (최근 연도)
    ni_latest  = ni_row.iloc[0] if ni_row is not None else np.nan
    results["net_margin"] = (ni_latest / rev_latest) if rev_latest else np.nan

    # 6. ROE — info에서 직접 제공
    results["roe"] = _safe_get(info, "returnOnEquity")

    # 7. ROIC = EBIT*(1-t) / (Total Equity + Total Debt)
    ebit_row   = _row(fin, "EBIT", "Operating Income")
    eq_row     = _row(bal, "Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity")
    debt_row   = _row(bal, "Total Debt", "Long Term Debt")

    if ebit_row is not None and eq_row is not None:
        ebit  = float(ebit_row.iloc[0])
        eq    = float(eq_row.iloc[0])
        debt  = float(debt_row.iloc[0]) if debt_row is not None else 0
        tax   = _safe_get(info, "effectiveTaxRate", default=0.21)
        nopat = ebit * (1 - tax)
        ic    = eq + debt
        results["roic"] = (nopat / ic) if ic else np.nan
    else:
        results["roic"] = np.nan

    # 8. Debt/Equity
    results["debt_to_equity"] = _safe_get(info, "debtToEquity")
    if not np.isnan(results["debt_to_equity"]):
        results["debt_to_equity"] /= 100   # yfinance가 % 단위로 반환

    # 9. Interest Coverage = EBIT / Interest Expense
    int_row = _row(fin, "Interest Expense")
    if ebit_row is not None and int_row is not None:
        ebit_v = float(ebit_row.iloc[0])
        int_v  = abs(float(int_row.iloc[0]))
        results["interest_coverage"] = (ebit_v / int_v) if int_v else np.nan
    else:
        results["interest_coverage"] = np.nan

    # 10. Profitability streak — 몇 년 연속 Net Income > 0
    if ni_row is not None:
        ni_vals = ni_row.astype(float).values   # 최근→과거
        streak = 0
        for v in ni_vals:
            if v > 0:
                streak += 1
            else:
                break
        results["profit_streak"] = streak
    else:
        results["profit_streak"] = 0

    return results


# ── scoring ──────────────────────────────────────────────────────────────────

QUALITY_CRITERIA = {
    "revenue_cagr":       {"label": "Revenue CAGR",       "threshold": 0.10, "unit": "%",  "multiply": 100},
    "ni_cagr":            {"label": "Net Income CAGR",    "threshold": 0.10, "unit": "%",  "multiply": 100},
    "fcf_cagr":           {"label": "FCF CAGR",           "threshold": 0.08, "unit": "%",  "multiply": 100},
    "gross_margin":       {"label": "Gross Margin",       "threshold": 0.40, "unit": "%",  "multiply": 100},
    "net_margin":         {"label": "Net Margin",         "threshold": 0.10, "unit": "%",  "multiply": 100},
    "roe":                {"label": "ROE",                "threshold": 0.15, "unit": "%",  "multiply": 100},
    "roic":               {"label": "ROIC",               "threshold": 0.12, "unit": "%",  "multiply": 100},
    "debt_to_equity":     {"label": "Debt / Equity",      "threshold": 1.0,  "unit": "x",  "multiply": 1,   "lower_is_better": True},
    "interest_coverage":  {"label": "Interest Coverage",  "threshold": 5.0,  "unit": "x",  "multiply": 1},
    "profit_streak":      {"label": "Profit Streak",      "threshold": 4,    "unit": "yrs","multiply": 1},
}

QUALITY_EXPLANATIONS = {
    "revenue_cagr":      "매출 성장률 (5Y CAGR). 10% 이상이면 꾸준히 사업이 확장되고 있음을 의미.",
    "ni_cagr":           "순이익 성장률 (5Y CAGR). 매출 성장이 실제 이익으로 이어지는지 확인.",
    "fcf_cagr":          "잉여현금흐름 성장률. 회계 이익이 아닌 실제 현금창출력 증가 여부.",
    "gross_margin":      "매출총이익률. 40% 이상이면 강한 가격 결정력 또는 경쟁 해자 존재.",
    "net_margin":        "순이익률. 10% 이상이면 비용 통제가 잘 되고 있음.",
    "roe":               "자기자본이익률. 주주가 맡긴 돈으로 얼마나 이익을 내는지. 15% 이상 선호.",
    "roic":              "투하자본이익률. WACC보다 높아야 기업이 실질 가치를 창출하고 있음. 12% 기준.",
    "debt_to_equity":    "부채/자본 비율. 1.0 이하이면 재무 레버리지가 안전한 수준.",
    "interest_coverage": "이자보상배율 = EBIT / 이자비용. 5x 이상이면 부채 상환 부담이 낮음.",
    "profit_streak":     "최근 몇 년 연속 흑자인지. 4년 이상 연속 흑자 = 안정적 수익 구조.",
}


def score_quality(metrics: dict) -> tuple[int, list[dict]]:
    """
    Returns:
        total_score: 0–10 (각 항목 pass=1)
        details: 항목별 pass/fail + 표시값 + 설명 list
    """
    details = []
    passed  = 0

    for key, cfg in QUALITY_CRITERIA.items():
        raw   = metrics.get(key, np.nan)
        lower = cfg.get("lower_is_better", False)

        if np.isnan(raw) if isinstance(raw, float) else False:
            status = "N/A"
        else:
            status = "PASS" if (raw <= cfg["threshold"] if lower else raw >= cfg["threshold"]) else "FAIL"

        if status == "PASS":
            passed += 1

        display = f"{raw * cfg['multiply']:.1f}{cfg['unit']}" if not (isinstance(raw, float) and np.isnan(raw)) else "N/A"

        details.append({
            "label":       cfg["label"],
            "value":       display,
            "threshold":   f"{'≤' if lower else '≥'} {cfg['threshold'] * cfg['multiply']:.0f}{cfg['unit']}",
            "status":      status,
            "explanation": QUALITY_EXPLANATIONS[key],
        })

    return passed, details