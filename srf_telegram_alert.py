import os
import sys
import time
import urllib.request
import urllib.parse
import json

try:
    import shioaji as sj
except ImportError:
    print("❌ 尚未安裝 shioaji 套件，請執行: pip install shioaji")
    sys.exit(1)

# ==========================================
# ⚙️ 配置區 (請填入您的 Telegram 與 Shioaji 金鑰)
# ==========================================
TG_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TG_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# 警報價格設定 (小型0050期貨 SRF)
ALERT_BUY_PRICE = 106.7      # 累計跌5% (季線加碼點)
ALERT_STOP_LOSS = 104.8     # 停損離場點

# 防洗版機制設定 (冷卻時間，秒)
COOLDOWN_TIME = 900          # 15分鐘內同類型警報只發一次
last_alert_time = {"buy": 0, "stop_loss": 0}

def send_telegram_msg(msg):
    """呼叫 Telegram Bot API 發送警報訊息"""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    
    try:
        with urllib.request.urlopen(req) as res:
            return res.status == 200
    except Exception as e:
        print(f"⚠️ Telegram 發送失敗: {e}")
        return False

def setup_alerts(api):
    # 定位合約
    target_code = "SRFN6"
    try:
        contract = api.Contracts.Futures[target_code]
        print(f"✅ 成功定位 {target_code} 合約，準備訂閱即時 Tick...")
    except KeyError:
        print(f"❌ 未能定位 {target_code} 合約！")
        return

    # 定期期貨報價回調函數
    @api.quote.set_on_tick_futs_v1_callback
    def on_tick_futs(exchange, tick):
        # 取得最新成交價
        price = float(tick.close)
        current_time = time.time()
        
        print(f"🔔 [即時成交] 價格: {price:.2f} 元 | 漲跌: {tick.change:+.2f} | 時間: {tick.time}")

        # 1. 觸及買進警報點
        if price <= ALERT_BUY_PRICE:
            if current_time - last_alert_time["buy"] > COOLDOWN_TIME:
                msg = (
                    f"🟢 <b>小型0050期貨到價提醒</b>\n"
                    f"商品代碼: {target_code}\n"
                    f"最新成交價: <b>{price:.2f} 元</b>\n"
                    f"🎯 已跌破季線買點 <b>{ALERT_BUY_PRICE:.2f} 元</b>，適合進行分批建倉！"
                )
                if send_telegram_msg(msg):
                    last_alert_time["buy"] = current_time
                    print("🚀 買進警報 Telegram 發送成功！")

        # 2. 觸及停損警報點
        if price <= ALERT_STOP_LOSS:
            if current_time - last_alert_time["stop_loss"] > COOLDOWN_TIME:
                msg = (
                    f"🔴 <b>🚨 小型0050期貨【停損警報】</b>\n"
                    f"商品代碼: {target_code}\n"
                    f"最新成交價: <b>{price:.2f} 元</b>\n"
                    f"💥 已跌破硬停損線 <b>{ALERT_STOP_LOSS:.2f} 元</b>！建議果斷平倉防守！"
                )
                if send_telegram_msg(msg):
                    last_alert_time["stop_loss"] = current_time
                    print("🚨 停損警報 Telegram 發送成功！")

    # 訂閱 SRF 行情 (Tick 資料)
    api.quote.subscribe(contract, tick=True)
    print("📈 即時行情監控中... (按下 Ctrl + C 可結束)")
    
    # 保持主執行緒運行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 停止監控，正在取消訂閱與登出...")
        api.quote.unsubscribe(contract, tick=True)

def main():
    api_key = os.environ.get("SHIOAJI_API_KEY") or input("🔑 API Key: ").strip()
    secret_key = os.environ.get("SHIOAJI_SECRET_KEY") or getpass.getpass("🔑 Secret Key: ").strip()

    api = sj.Shioaji()
    try:
        api.login(api_key=api_key, secret_key=secret_key)
        setup_alerts(api)
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
    finally:
        api.logout()
        print("🔓 已登出永豐 API")

if __name__ == '__main__':
    main()
