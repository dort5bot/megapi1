import requests, json, csv, os
from datetime import datetime
import numpy as np
import pandas as pd

FAV_FILE = "ap_favorites.json"
HISTORY_FILE = "ap_history.csv"
ALERT_FILE = "ap_alerts.json"

# -------- Public API --------
def get_24h_tickers():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    return requests.get(url).json()

# ====================================================
# ✅ VWAP Tabanlı Skor Hesaplama ( /ap için )
# ====================================================
def calculate_scores():
    data = get_24h_tickers()
    alt_vwap_sum, alt_vol_sum = 0, 0
    alt_vs_btc_sum, alt_vs_btc_vol = 0, 0
    long_term_volumes = []
    btc_vwap = 0

    for coin in data:
        sym = coin['symbol']
        if not sym.endswith("USDT") or sym in ["BUSDUSDT","USDCUSDT","FDUSDUSDT"]:
            continue

        price_change = float(coin['priceChangePercent'])
        volume = float(coin['quoteVolume'])

        if sym == "BTCUSDT":
            btc_vwap = price_change
            continue

        alt_vwap_sum += price_change * volume
        alt_vol_sum += volume

        if price_change > btc_vwap:
            alt_vs_btc_sum += (price_change - btc_vwap) * volume
            alt_vs_btc_vol += volume

        long_term_volumes.append(volume)

    alt_vwap = alt_vwap_sum / alt_vol_sum if alt_vol_sum else 0
    alt_vs_btc_vwap = alt_vs_btc_sum / alt_vs_btc_vol if alt_vs_btc_vol else 0
    long_term_score = sum(long_term_volumes) / len(long_term_volumes) / 1_000_000 if long_term_volumes else 0

    alt_vs_btc_score = round(min(100, max(0, alt_vs_btc_vwap + 50)), 1)
    alt_total_score = round(min(100, max(0, alt_vwap + 50)), 1)
    long_term_score = round(min(100, max(0, long_term_score)), 1)

    return alt_vs_btc_score, alt_total_score, long_term_score

# ====================================================
# ✅ Günlük Kayıt ve Trend ( /ap için )
# ====================================================
def save_daily_history():
    vsbtc, alt, longt = calculate_scores()
    date = datetime.now().strftime("%Y-%m-%d")
    rows = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            rows = list(csv.reader(f))
    rows.append([date, vsbtc, alt, longt])
    if len(rows) > 60:
        rows = rows[-60:]
    with open(HISTORY_FILE, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    return vsbtc, alt, longt

def compare_with_history(days=1):
    if not os.path.exists(HISTORY_FILE):
        return calculate_scores(), [0,0,0], ["➡️","➡️","➡️"]
    with open(HISTORY_FILE, "r") as f:
        rows = list(csv.reader(f))
    if len(rows) < days:
        return calculate_scores(), [0,0,0], ["➡️","➡️","➡️"]

    now = calculate_scores()
    if days == 1:
        base = [float(rows[-1][1]), float(rows[-1][2]), float(rows[-1][3])]
    else:
        base = [sum(float(r[i]) for r in rows[-days:]) / days for i in range(1, 4)]

    diff = [round(((n - b) / b) * 100, 1) if b else 0 for n, b in zip(now, base)]
    arrows = ["🔺" if d > 0 else "🔻" if d < 0 else "➡️" for d in diff]
    return now, diff, arrows

def ap_command(period="24h", days=None):
    now, diff, arr = compare_with_history(days if days else 1)
    return (f"Ap({period}) raporu\n"
            f"Altların Kısa Vadede Btc'ye Karşı Gücü(0-100): {now[0]} {arr[0]}%{abs(diff[0])}\n"
            f"Altların Kısa Vadede Gücü(0-100): {now[1]} {arr[1]}%{abs(diff[1])}\n"
            f"Coinlerin Uzun Vadede Gücü(0-100): {now[2]} {arr[2]}%{abs(diff[2])}")

# ====================================================
# ✅ P Komutu (Fiyat, % değişim, hacim)
# ====================================================
def p_command(coins):
    data = get_24h_tickers()
    lookup = {d['symbol']: d for d in data}
    msg = ""
    for c in coins:
        s = (c.upper() + "USDT")
        if s not in lookup:
            msg += f"{c.upper()}: bulunamadı\n"
            continue
        d = lookup[s]
        price = float(d['lastPrice'])
        change = float(d['priceChangePercent'])
        vol = float(d['quoteVolume']) / 1_000_000
        pf = f"{price:.2f}" if price >= 1 else f"{price:.8f}"
        arrow = "🔺" if change > 0 else "🔻" if change < 0 else "➡️"
        msg += f"{c.upper()}: {pf} {arrow}{change}% (Vol: {vol:.1f}M$)\n"
    return msg

# ====================================================
# ✅ Favoriler
# ====================================================
def load_favorites():
    if os.path.exists(FAV_FILE):
        with open(FAV_FILE, "r") as f:
            return json.load(f)
    return {}

def save_favorites(data):
    with open(FAV_FILE, "w") as f:
        json.dump(data, f)

def add_favorite(fav, coins):
    favs = load_favorites()
    favs[fav] = coins
    save_favorites(favs)
    return f"{fav} güncellendi: {' '.join(coins)}"

def delete_favorite(fav):
    favs = load_favorites()
    if fav in favs:
        del favs[fav]
        save_favorites(favs)
        return f"{fav} silindi"
    return "Favori bulunamadı"

# ====================================================
# ✅ Alert
# ====================================================
def set_alert_threshold(level1, level2):
    alert = {"level1": float(level1), "level2": float(level2)}
    with open(ALERT_FILE, "w") as f:
        json.dump(alert, f)
    return f"Alertler güncellendi: {level1}, {level2}"

# ====================================================
# ✅ RSI + MACD Trend Analizi ( /trend için )
# ====================================================
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"

def get_klines(symbol="BTCUSDT", interval="1h", limit=100):
    url = f"{BINANCE_KLINES}?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    return [float(x[4]) for x in data]

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.convolve(gains, np.ones(period), 'valid') / period
    avg_loss = np.convolve(losses, np.ones(period), 'valid') / period
    rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss != 0)
    rsi = 100 - (100 / (1 + rs))
    return rsi[-1] if len(rsi) else 0

def calculate_macd(prices, short=12, long=26, signal=9):
    short_ema = pd.Series(prices).ewm(span=short, adjust=False).mean()
    long_ema = pd.Series(prices).ewm(span=long, adjust=False).mean()
    macd_line = short_ema - long_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line.iloc[-1], signal_line.iloc[-1], hist.iloc[-1]

def interpret_rsi_macd(rsi, macd, signal, hist):
    trend = ""
    if rsi > 70:
        trend += "🔴 RSI: Aşırı Alım"
    elif rsi < 30:
        trend += "🟢 RSI: Aşırı Satım"
    else:
        trend += "⚪ RSI: Nötr"

    if macd > signal and hist > 0:
        trend += " | 📈 MACD: Yükseliş"
    elif macd < signal and hist < 0:
        trend += " | 📉 MACD: Düşüş"
    else:
        trend += " | ➡️ MACD: Kararsız"
    return trend

def rsi_macd_command(coins):
    msg = "📊 RSI & MACD Trend Analizi\n"
    for c in coins:
        sym = c.upper() + "USDT"
        try:
            closes = get_klines(sym)
            rsi = round(calculate_rsi(closes), 2)
            macd, signal, hist = calculate_macd(closes)
            tr = interpret_rsi_macd(rsi, macd, signal, hist)
            msg += f"\n{c.upper()}: RSI={rsi}, MACD={macd:.2f}, Signal={signal:.2f} → {tr}"
        except Exception as e:
            msg += f"\n{c.upper()}: Veri alınamadı ({e})"
    return msg