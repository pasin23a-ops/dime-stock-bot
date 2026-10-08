import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta

# ==========================================
# ⚙️ ตั้งค่าข้อมูลบอท Dime!
# ==========================================
TELEGRAM_BOT_TOKEN = "8938668097:AAFmVzQa6qIefASoTo2WfKk4FRytQyRPcJw"
TELEGRAM_CHAT_ID = "8644030650"

# รายชื่อหุ้นอเมริกาใน Dime! ที่ต้องการวิเคราะห์
WATCHLIST = ["NVDA", "AAPL", "TSLA", "MSFT", "PLTR", "AMZN", "GOOGL"]

# เป้าหมายกำไร (%)
PROFIT_TARGET_PCT = 10.0

# ==========================================
# 📊 ฟังก์ชั่นคำนวณเทคนิคัล
# ==========================================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_average_cycle_days(df):
    rsi = df['RSI']
    periods = []
    in_buy = False
    buy_date = None

    for i in range(len(df)):
        if not in_buy and rsi.iloc[i] <= 42:
            in_buy = True
            buy_date = df.index[i]
        elif in_buy and rsi.iloc[i] >= 60:
            in_buy = False
            sell_date = df.index[i]
            days = (sell_date - buy_date).days
            if days > 0:
                periods.append(days)

    return int(np.mean(periods)) if len(periods) > 0 else 14

def send_telegram_message(message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            res = requests.post(url, data=payload, timeout=10)
            if res.status_code != 200:
                print(f"⚠️ เกิดข้อผิดพลาด Telegram API: {res.text}")
        except Exception as e:
            print(f"⚠️ ส่ง Telegram ไม่สำเร็จ: {e}")

# ==========================================
# 🚀 ระบบประมวลผลสัญญาณหุ้น
# ==========================================
def run_dime_bot():
    print(f"\n⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] กำลังประมวลผลวิเคราะห์หุ้น...")
    all_reports = []
    alert_reports = []

    for ticker in WATCHLIST:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty:
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['RSI'] = calculate_rsi(df['Close'], period=14)
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()

        last_date = df.index[-1]
        last_price = float(df['Close'].iloc[-1])
        last_rsi = float(df['RSI'].iloc[-1])
        cycle_days = get_average_cycle_days(df)

        buy_price = last_price
        sell_price = buy_price * (1 + (PROFIT_TARGET_PCT / 100.0))
        stop_loss = buy_price * 0.95
        est_sell_date = last_date + timedelta(days=cycle_days)

        if last_rsi <= 42:
            status_emoji = "🟢"
            status_text = "เข้าเขตน่าซื้อ (BUY ZONE)"
            is_alert = True
        elif last_rsi >= 65:
            status_emoji = "🔴"
            status_text = "เข้าเขตควรขาย (SELL ZONE)"
            is_alert = True
        else:
            status_emoji = "🟡"
            status_text = "ถือรอจังหวะ (HOLD/WAIT)"
            is_alert = False

        report = (
            f"{status_emoji} *[Dime! Stock]* `{ticker}`\n"
            f"💵 ราคาปัจจุบัน: `${last_price:.2f}` (RSI: {last_rsi:.1f})\n"
            f"📌 สถานะ: *{status_text}*\n"
            f"------------------------------\n"
            f"📥 *ราคาที่แนะนำซื้อ*: `${buy_price:.2f}`\n"
            f"🎯 *เป้าขายทำกำไร (+{PROFIT_TARGET_PCT}%)*: `${sell_price:.2f}`\n"
            f"🛡️ *จุดตัดขาดทุน (-5%)*: `${stop_loss:.2f}`\n"
            f"⏱️ *รอบวิ่งเฉลี่ย*: ~{cycle_days} วัน\n"
            f"📆 *คาดการณ์วันขาย*: `{est_sell_date.strftime('%Y-%m-%d')}`"
        )

        print(f"[{ticker}] RSI: {last_rsi:.1f} -> {status_text}")
        all_reports.append(report)
        if is_alert:
            alert_reports.append(report)

    if alert_reports:
        msg = "📢 *รายงานสัญญาณเฝ้าระวังหุ้น Dime! วันนี้*\n\n" + "\n\n".join(alert_reports)
        send_telegram_message(msg)
        print("✅ ส่งแจ้งเตือนหุ้นติดสัญญาณเข้า Telegram เรียบร้อย!")
    else:
        msg = "📊 *รายงานสรุปหุ้น Dime! วันนี้*\n\n*(ยังไม่มีหุ้นตัวไหนเข้าเขตโซนซื้อหรือขายชัดเจน)*\n\n" + "\n\n".join(all_reports[:3])
        send_telegram_message(msg)
        print("ℹ️ ส่งรายงานสรุปทั่วไปเข้า Telegram เรียบร้อย!")

if __name__ == "__main__":
    run_dime_bot()
