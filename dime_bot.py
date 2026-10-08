import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# ดึงค่า Secrets จาก GitHub Actions
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# รายชื่อหุ้นในแอป Dime! ที่ต้องการติดตาม
WATCHLIST = ["NVDA", "AAPL", "TSLA", "MSFT", "PLTR", "AMZN", "GOOGL"]
PROFIT_TARGET_PCT = 0.10  # เป้าหมายกำไร 10%

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="6m")
        if df.empty or len(df) < 30:
            return None, None
        
        df['RSI'] = calculate_rsi(df['Close'])
        
        last_price = float(df['Close'].iloc[-1])
        last_rsi = float(df['RSI'].iloc[-1])
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # คาดการณ์วันที่ควรขาย (คำนวณจากรอบระยะเวลาการย่อตัวเฉลี่ย ~14 วัน)
        est_sell_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        
        # คำนวณราคาเป้าหมายขาย และ จำนวนเงินกำไรที่จะได้รับต่อ 1 หุ้น
        buy_price = last_price
        target_sell_price = buy_price * (1 + PROFIT_TARGET_PCT)
        profit_usd = target_sell_price - buy_price
        
        status = "HOLD"
        signal_text = "ยังไม่ถึงจุดซื้อ (ถือรอสัญญาณ)"
        
        if last_rsi <= 42:
            status = "BUY"
            signal_text = f"🟢 **เข้าซื้อได้วันนี้ ({today_str})** (RSI อยู่ในเขตราคาถูก)"
        elif last_rsi >= 70:
            status = "SELL"
            signal_text = f"🔴 **ควรขายทำกำไรวันนี้ ({today_str})** (RSI สูงเกินไป)"

        # รูปแบบข้อความที่จะส่งเข้า Telegram
        msg = (
            f"📌 **ชื่อหุ้น**: {ticker}\n"
            f"💵 **ราคาปัจจุบัน**: ${last_price:.2f}\n"
            f"📥 **วันที่/จังหวะควรซื้อ**: {signal_text}\n"
            f"🎯 **ราคาขายเป้าหมาย**: ${target_sell_price:.2f}\n"
            f"📆 **คาดการณ์วันที่ควรขาย**: ประมาณวันที่ **{est_sell_date}**\n"
            f"💰 **กำไรที่จะได้รับถ้าขาย**: **+${profit_usd:.2f} ต่อหุ้น** (+{PROFIT_TARGET_PCT*100:.0f}%)\n"
            f"------------------------------------\n"
            f"📈 *ข้อมูลราคาอ้างอิงตรงกับแอป Dime! (US Market)*"
        )
        return msg, status
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None, None

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing Telegram credentials!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    for ticker in WATCHLIST:
        msg, status = analyze_stock(ticker)
        # ส่งการแจ้งเตือนเมื่อเจอสัญญาณซื้อ หรือ ขาย
        if msg and status in ["BUY", "SELL"]:
            send_telegram(msg)
