import os
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta

# ==========================================
# ⚙️ ตั้งค่าข้อมูลบอท Dime!
# ==========================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8921769324:AAHQCNuzUumIRk5j-spPd3T0DY9KkDtApYk")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8644030650")

# 🚀 รายชื่อหุ้นยอดฮิตบน Dime!
WATCHLIST = [
    "NVDA", "AAPL", "TSLA", "MSFT", "PLTR", 
    "AMZN", "GOOGL", "META", "AMD", "NFLX", 
    "COIN", "SPY", "QQQ"
]

PROFIT_TARGET_PCT = 10.0  # เป้ากำไร +10%
STOP_LOSS_PCT = 5.0      # คัดขาดทุน -5%

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
# 🚀 ระบบประมวลผลวิเคราะห์หุ้นเพื่อกำไรจริง
# ==========================================
def run_dime_bot():
    print(f"\n⏰ [{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] กำลังวิเคราะห์หุ้น Dime!...")
    all_reports = []
    alert_reports = []

    today_str = datetime.now().strftime('%d/%m/%Y')

    for ticker in WATCHLIST:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 50:
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['RSI'] = calculate_rsi(df['Close'], period=14)
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()

        last_price = float(df['Close'].iloc[-1])
        last_rsi = float(df['RSI'].iloc[-1])
        ema50 = float(df['EMA50'].iloc[-1])
        
        is_uptrend = last_price > ema50
        cycle_days = get_average_cycle_days(df)

        buy_price = last_price
        sell_price = buy_price * (1 + (PROFIT_TARGET_PCT / 100.0))
        profit_usd = sell_price - buy_price
        stop_loss = buy_price * (1 - (STOP_LOSS_PCT / 100.0))
        
        est_sell_date = (datetime.now() + timedelta(days=cycle_days)).strftime('%d/%m/%Y')

        if last_rsi <= 42 and is_uptrend:
            status_emoji = "🟢"
            status_header = "BUY (น่าเข้าซื้อมาก)"
            advice = "🔥 *หุ้นย่อตัวในขาขึ้น* (โอกาสชนะสูงมาก)"
            is_alert = True
        elif last_rsi <= 40 and not is_uptrend:
            status_emoji = "⚠️"
            status_header = "RISKY BUY (ซื้อได้แต่เสี่ยง)"
            advice = "⚡ *หุ้นอยู่ขาลง* ควรแบ่งไม้เล็กๆ เท่านั้น"
            is_alert = True
        elif last_rsi >= 68:
            status_emoji = "🔴"
            status_header = "SELL (ควรขายทำกำไร)"
            advice = "💰 *เข้าเขตราคาแพง* แนะนำแบ่งขายเก็บกำไร"
            is_alert = True
        else:
            status_emoji = "🟡"
            status_header = "HOLD / WAIT (ถือ/รอจังหวะ)"
            advice = "⏳ *ราคากลางๆ* รอสัญญาณย่อตัวค่อยซื้อ"
            is_alert = False

        report = (
            f"{status_emoji} *{ticker}* | *{status_header}*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *ราคาปัจจุบัน*: `${last_price:.2f}` (RSI: {last_rsi:.1f})\n"
            f"📅 *วันที่ควรซื้อ*: `{today_str}`\n"
            f"📥 *ราคาที่แนะนำซื้อ*: `${buy_price:.2f}`\n"
            f"🎯 *เป้าขายทำกำไร (+{PROFIT_TARGET_PCT:.0f}%):* `${sell_price:.2f}`\n"
            f"💰 *กำไรคาดการณ์*: `+${profit_usd:.2f} / หุ้น`\n"
            f"🛡️ *จุดตัดขาดทุน (-{STOP_LOSS_PCT:.0f}%):* `${stop_loss:.2f}`\n"
            f"📆 *คาดการณ์วันขาย*: `{est_sell_date}` (~{cycle_days} วัน)\n"
            f"💡 *กลยุทธ์*: {advice}\n"
        )

        print(f"[{ticker}] RSI: {last_rsi:.1f} | Uptrend: {is_uptrend} -> {status_header}")
        all_reports.append(report)
        if is_alert:
            alert_reports.append(report)

    if alert_reports:
        msg = "📢 *[Dime! - เวอร์ชันใหม่ 2.0] รายงานสัญญาณหุ้นวันนี้*\n" + "*(คัดเฉพาะตัวที่มีโอกาสทำกำไรสูง)*\n\n" + "\n".join(alert_reports)
        send_telegram_message(msg)
        print("✅ ส่งแจ้งเตือนหุ้นติดสัญญาณเข้า Telegram เรียบร้อย!")
    else:
        msg = "📊 *[Dime! - เวอร์ชันใหม่ 2.0] สรุปภาพรวมหุ้นวันนี้*\n\n*(ยังไม่มีหุ้นตัวไหนย่อตัวเข้าจุดซื้อที่ปลอดภัย)*\n\n" + "\n".join(all_reports[:3])
        send_telegram_message(msg)
        print("ℹ️ ส่งรายงานสรุปทั่วไปเข้า Telegram เรียบร้อย!")

if __name__ == "__main__":
    run_dime_bot()
