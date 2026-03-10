import logging
import time
import requests
import threading
import re
import os
import random
from flask import Flask, jsonify
import cloudscraper # 🟢 Cloudflare Bypass Library

# 🟢 Render-এ গ্যারান্টিড লগ দেখানোর জন্য প্রফেশনাল লগার
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.StreamHandler()])
logger = logging.getLogger()

app = Flask(__name__)
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

bot_state = {
    "1_status": "Starting Stealth Mode Server...",
    "2_mk_login": False,
    "3_last_signal_from_pc": "Unknown",
    "4_last_sync_time": "Never",
    "5_latest_error": "None"
}

# 🟢 Cloudscraper Session (Cloudflare কে বোকা বানানোর জন্য)
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    }
)
api_session = requests.Session()

def login_to_mk():
    try:
        logger.info("Fetching MK Login Page (Stealth Mode)...")
        res = scraper.get("http://mknetworkbd.com/auth.php", timeout=20)
        
        email_name, pass_name = "email", "password"
        for inp in re.findall(r'<input([^>]+)>', res.text, re.IGNORECASE):
            name_match = re.search(r'name=["\']([^"\']+)["\']', inp, re.IGNORECASE)
            if name_match:
                if 'password' in inp.lower(): pass_name = name_match.group(1)
                elif 'email' in inp.lower() or 'user' in inp.lower(): email_name = name_match.group(1)
        
        payload = {email_name: "sohan.shahel.sifa@gmail.com", pass_name: "Sohan123@@##", "login": "1", "submit": "1", "t-btnlog": "1"}
        login_res = scraper.post("http://mknetworkbd.com/auth.php", data=payload, timeout=20)
        
        if "dashboard" in login_res.text.lower() or "logout" in login_res.text.lower():
            bot_state["2_mk_login"] = True
            bot_state["1_status"] = "Logged In (Stealth)"
            logger.info("✅ Login Success!")
            return True
        else:
            bot_state["1_status"] = "Login Failed!"
            logger.warning("❌ Login Failed! Retrying...")
            return False
    except Exception as e:
        bot_state["5_latest_error"] = f"Login Error: {e}"
        logger.error(bot_state["5_latest_error"])
        return False

def sync_data():
    try:
        current_time = int(time.time())
        
        # 🟢 Signal Check from PC
        sig_url = f"{API_BRIDGE_URL}?action=check_signal&_t={current_time}"
        sig_req = api_session.get(sig_url, headers={"User-Agent": "Render-Bot-Server"}, timeout=15)
        
        if sig_req.status_code != 200:
            bot_state["5_latest_error"] = f"AwardSpace Error! Code: {sig_req.status_code}"
            return False
            
        try:
            sig_res = sig_req.json()
        except:
            return False
            
        bot_state["3_last_signal_from_pc"] = sig_res.get("signal", "WAIT")
        
        if bot_state["3_last_signal_from_pc"] == "GET":
            logger.info("🔔 SIGNAL RECEIVED! Fetching new number from MK...")
            api_session.get(f"{API_BRIDGE_URL}?action=signal_received&_t={current_time}", timeout=10)
            
            try:
                range_req = api_session.get(f"{API_BRIDGE_URL}?action=get_range&_t={current_time}", timeout=10).json()
                target_range = range_req.get('range', '')
                
                num_payload = {"service": "fb", "range": target_range, "getBtn": "1"} 
                
                # 🟢 Random Delay (মানুষের মতো ক্লিক করার জন্য)
                time.sleep(random.uniform(1.5, 3.5))
                fetch_res = scraper.post("http://mknetworkbd.com/getnum.php", data=num_payload, timeout=20)
                
                if "login" in fetch_res.url.lower():
                    logger.warning("⚠️ Session expired during fetch. Relogging...")
                    bot_state["2_mk_login"] = False
                    return False
            except Exception as fe:
                logger.error(f"Fetch Error: {fe}")

        # 🟢 Read Numbers & OTPs
        time.sleep(random.uniform(2.0, 4.0)) # 🟢 Random Delay
        table_res = scraper.get("http://mknetworkbd.com/getnum.php", timeout=20)
        
        if "login" in table_res.url.lower():
            logger.warning("⚠️ Session expired during table read. Relogging...")
            bot_state["2_mk_login"] = False
            return False

        rows = re.findall(r'<tr.*?>(.*?)</tr>', table_res.text, re.DOTALL | re.IGNORECASE)
        bulk_data = []
        
        for row in rows[:25]:
            cols = re.findall(r'<td.*?>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
            if len(cols) >= 2:
                raw_phone = re.sub(r'<.*?>', ' ', cols[0]) 
                phone_match = re.search(r'(\d{10,15})', raw_phone)
                if not phone_match: continue
                phone = phone_match.group(1)
                
                status_text = re.sub(r'<.*?>', ' ', cols[1]).strip()
                otp = "N/A"
                otp_match = re.search(r'\b\d{4,6}\b', status_text)
                if otp_match: otp = otp_match.group(0)
                
                net_status = "PENDING"
                if "SUCCESS" in status_text.upper() or otp != "N/A": net_status = "SUCCESS"
                elif "CANCELED" in status_text.upper() or "EXPIRED" in status_text.upper(): net_status = "FAILED"
                
                bulk_data.append({"phone": phone, "otp": otp, "status": net_status})
                
        if bulk_data:
            api_session.post(f"{API_BRIDGE_URL}?action=save_bulk_numbers", json={"numbers": bulk_data}, timeout=15)
            bot_state["4_last_sync_time"] = f"Synced {len(bulk_data)} numbers at {time.strftime('%H:%M:%S')}"
            logger.info(bot_state["4_last_sync_time"])
        
        return True
    except Exception as e:
        bot_state["5_latest_error"] = f"Sync Error: {e}"
        logger.error(bot_state["5_latest_error"])
        return False

def background_loop():
    logger.info("Background Thread Started (Stealth Mode)!")
    while True:
        if not bot_state["2_mk_login"]:
            login_to_mk()
            time.sleep(10)
        else:
            sync_data()
            # 🟢 15 সেকেন্ডের স্লিপ (AwardSpace এবং MK Network এর লিমিট থেকে বাঁচতে)
            time.sleep(15) 

bot_thread = threading.Thread(target=background_loop, daemon=True)
bot_thread.start()

@app.route('/')
def home():
    return jsonify(bot_state)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
