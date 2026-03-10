import json

from src.data import get_datasource


def get_stock_data(ticker: str, period: str = "1y") -> dict:
    """
    주식의 일봉 OHLCV 데이터와 기본 통계를 반환합니다.

    Args:
        ticker: 종목 코드. 미국 주식은 티커 심볼(예: AAPL), 한국 주식은 6자리 숫자(예: 005930)
        period: 조회 기간. "3mo", "6mo", "1y", "2y", "5y" 중 하나 (기본값: "1y")

    Returns:
        종목 정보, 최근 가격, 기간 내 통계(최고/최저/평균/수익률)를 담은 dict
    """
    try:
        ds = get_datasource(ticker)
        info = ds.get_info(ticker)
        df = ds.get_ohlcv(ticker, period)

        latest = df.iloc[-1]
        period_return = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100

        return {
            "ticker": ticker,
            "name": info.name,
            "market": info.market,
            "currency": info.currency,
            "period": period,
            "total_days": len(df),
            "latest": {
                "date": str(df.index[-1].date()),
                "open": round(float(latest["open"]), 2),
                "high": round(float(latest["high"]), 2),
                "low": round(float(latest["low"]), 2),
                "close": round(float(latest["close"]), 2),
                "volume": int(latest["volume"]),
            },
            "stats": {
                "period_high": round(float(df["high"].max()), 2),
                "period_low": round(float(df["low"].min()), 2),
                "avg_close": round(float(df["close"].mean()), 2),
                "period_return_pct": round(float(period_return), 2),
                "avg_volume": int(df["volume"].mean()),
            },
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


def search_stock(query: str, market: str = "all") -> list[dict]:
    """
    종목명 또는 티커로 주식을 검색합니다.

    Args:
        query: 검색어 (종목명 또는 티커 일부)
        market: 검색 대상 시장. "us", "kr", "all" 중 하나 (기본값: "all")

    Returns:
        매칭된 종목 목록 (ticker, name, market, currency)
    """
    from src.data.kr import KRStockDataSource
    from src.data.us import USStockDataSource

    results = []
    try:
        if market in ("us", "all"):
            us_results = USStockDataSource().search(query)
            results.extend([
                {"ticker": s.ticker, "name": s.name, "market": s.market, "currency": s.currency}
                for s in us_results
            ])
        if market in ("kr", "all"):
            kr_results = KRStockDataSource().search(query)
            results.extend([
                {"ticker": s.ticker, "name": s.name, "market": s.market, "currency": s.currency}
                for s in kr_results
            ])
    except Exception as e:
        return [{"error": str(e)}]

    return results


def compare_stocks(tickers: list[str], metric: str = "performance", period: str = "1y") -> dict:
    """
    여러 종목을 비교 분석합니다.

    Args:
        tickers: 비교할 종목 코드 목록 (최대 5개)
        metric: 비교 기준. "performance"(수익률), "volatility"(변동성) 중 하나 (기본값: "performance")
        period: 비교 기간. "3mo", "6mo", "1y", "2y", "5y" 중 하나 (기본값: "1y")

    Returns:
        종목별 비교 결과와 순위
    """
    import numpy as np

    if len(tickers) > 5:
        tickers = tickers[:5]

    comparison = []
    for ticker in tickers:
        try:
            ds = get_datasource(ticker)
            info = ds.get_info(ticker)
            df = ds.get_ohlcv(ticker, period)

            returns = df["close"].pct_change().dropna()
            period_return = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
            volatility = float(returns.std() * (252 ** 0.5) * 100)  # 연환산

            comparison.append({
                "ticker": ticker,
                "name": info.name,
                "market": info.market,
                "period_return_pct": round(float(period_return), 2),
                "annualized_volatility_pct": round(volatility, 2),
                "latest_close": round(float(df["close"].iloc[-1]), 2),
                "currency": info.currency,
            })
        except Exception as e:
            comparison.append({"ticker": ticker, "error": str(e)})

    if metric == "performance":
        comparison.sort(key=lambda x: x.get("period_return_pct", float("-inf")), reverse=True)
    elif metric == "volatility":
        comparison.sort(key=lambda x: x.get("annualized_volatility_pct", float("inf")))

    return {"metric": metric, "period": period, "results": comparison}
