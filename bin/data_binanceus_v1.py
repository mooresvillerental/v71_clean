import urllib.request, json, time

def fetch_ohlc_binanceus(symbol: str, interval_min: int, since_ts: int, *, max_calls: int = 500):
    """
    Fetch Binance US klines for symbol like BTCUSDT at 5m.
    Returns: times_sec[], closes[] ascending.
    Pagination uses startTime (ms). limit=1000.
    """
    if interval_min != 5:
        raise ValueError("binanceus_v1 currently supports interval_min=5 only")

    interval = "5m"
    limit = 1000
    times = []
    closes = []

    start_ms = int(since_ts) * 1000
    calls = 0

    while calls < int(max_calls):
        url = f"https://api.binance.us/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}&startTime={start_ms}"
        raw = None
        last_err = None
        for _try in range(3):
            try:
                raw = urllib.request.urlopen(url, timeout=15).read().decode("utf-8", "replace")
                last_err = None
                break
            except Exception as e:
                last_err = e
                time.sleep(0.6 * (_try + 1))
        if raw is None:
            # give up gracefully; return what we have
            break
        data = json.loads(raw) if raw else []
        if not data:
            break

        added = 0
        last_open_ms = None
        for row in data:
            try:
                open_ms = int(row[0])
                close_px = float(row[4])
            except Exception:
                continue
            last_open_ms = open_ms
            t = open_ms // 1000
            if (not times) or (t > times[-1]):
                times.append(t)
                closes.append(close_px)
                added += 1

        calls += 1
        if added == 0 or last_open_ms is None:
            break

        # advance start_ms to next candle after last returned open time
        start_ms = last_open_ms + (interval_min * 60 * 1000)

        # tiny politeness delay
        time.sleep(0.05)

        # stop if we got less than full page (likely end)
        if len(data) < limit:
            break

    return times, closes
