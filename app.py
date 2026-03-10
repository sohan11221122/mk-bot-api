import logging
import time
import requests
import threading
import re
import os
from flask import Flask, jsonify

# 🟢 Render-এ গ্যারান্টিড লগ দেখানোর জন্য প্রফেশনাল লগার
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.StreamHandler()])
logger = logging.getLogger()

app = Flask(__name__)
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

# 🟢 বটের বর্তমান অবস্থা সেভ রাখার জন্য লাইভ ড্যাশবোর্ড
bot_state = {
    "1_status": "Starting Server...",
    "2_mk_login": False,
    "3_last_signal_from_pc": "Unknown",
    "4_last_sync_time": "Never",
    "5_latest_error": "None"
}

session = requests.Session()
api_session = requests.Session()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0",
    "Accept": "*/*"
}

def login_to_mk():
    try:
        logger.info("Fetching MK Login Page...")
        res = session.get("http://mknetworkbd.com/auth.php", headers=headers, timeout=15)
        
        email_name, pass_name = "email", "password"
        for inp in re.findall(r'<input([^>]+)>', res.text, re.IGNORECASE):
            name_match = re.search(r'name=["\']([^"\']+)["\']', inp, re.IGNORECASE)
            if name_match:
                if 'password' in inp.lower(): pass_name = name_match.group(1)
                elif 'email' in inp.lower() or 'user' in inp.lower(): email_name = name_match.group(1)
        
        payload = {email_name: "sohan.shahel.sifa@gmail.com", pass_name: "Sohan123@@##", "login": "1", "submit": "1", "t-btnlog": "1"}
        login_res = session.post("http://mknetworkbd.com/auth.php", data=payload, headers=headers, timeout=15)
        
        if "dashboard" in login_res.text.lower() or "logout" in login_res.text.lower():
            bot_state["2_mk_login"] = True
            bot_state["1_status"] = "Logged In & Running"
            logger.info("✅ Login Success!")
            return True
        else:
            bot_state["1_status"] = "Login Failed!"
            logger.warning("❌ Login Failed!")
            return False
    except Exception as e:
        bot_state["5_latest_error"] = f"Login Error: {e}"
        logger.error(bot_state["5_latest_error"])
        return False

def sync_data():
    try:
        current_time = int(time.time())
        
        # 🟢 Signal Check from PC (via AwardSpace)
        sig_url = f"{API_BRIDGE_URL}?action=check_signal&_t={current_time}"
        sig_req = api_session.get(sig_url, headers={"User-Agent": "Render-Bot-Server"}, timeout=10)
        
        if sig_req.status_code != 200:
            bot_state["5_latest_error"] = f"AwardSpace Blocked IP! Code: {sig_req.status_code}"
            logger.error(bot_state["5_latest_error"])
            return False
            
        try:
            sig_res = sig_req.json()
        except:
            bot_state["5_latest_error"] = "AwardSpace returned HTML instead of JSON. (Security Block)"
            logger.error(bot_state["5_latest_error"])
            return False
            
        bot_state["3_last_signal_from_pc"] = sig_res.get("signal", "WAIT")
        
        if bot_state["3_last_signal_from_pc"] == "GET":
            logger.info("🔔 SIGNAL RECEIVED! Getting new number...")
            api_session.get(f"{API_BRIDGE_URL}?action=signal_received&_t={current_time}", timeout=5)
            range_req = api_session.get(f"{API_BRIDGE_URL}?action=get_range&_t={current_time}", timeout=5).json()
            num_payload = {"service": "fb", "range": range_req.get('range', ''), "getBtn": "1"} 
            session.post("http://mknetworkbd.com/getnum.php", data=num_payload, headers=headers, timeout=10)

        # 🟢 Read Numbers & OTPs
        table_res = session.get("http://mknetworkbd.com/getnum.php", headers=headers, timeout=10)
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
            api_session.post(f"{API_BRIDGE_URL}?action=save_bulk_numbers", json={"numbers": bulk_data}, timeout=10)
            bot_state["4_last_sync_time"] = f"Synced {len(bulk_data)} numbers at {time.strftime('%H:%M:%S')}"
            logger.info(bot_state["4_last_sync_time"])
        
        return True
    except Exception as e:
        bot_state["5_latest_error"] = f"Sync Error: {e}"
        logger.error(bot_state["5_latest_error"])
        return False

def background_loop():
    logger.info("Background Thread Started!")
    while True:
        if not bot_state["2_mk_login"]:
            login_to_mk()
            time.sleep(5)
        else:
            sync_data()
            time.sleep(3) # ৩ সেকেন্ড পর পর রিফ্রেশ

# Start Thread
bot_thread = threading.Thread(target=background_loop, daemon=True)
bot_thread.start()

# 🟢 লাইভ ড্যাশবোর্ড (ব্রাউজারে দেখার জন্য)
@app.route('/')
def home():
    return jsonify(bot_state)

# 🟢 ম্যানুয়াল পুশ (বট আটকে গেলে ধাক্কা দেওয়ার জন্য)
@app.route('/force')
def force():
    if not bot_state["2_mk_login"]:
        login_to_mk()
    sync_data()
    return jsonify({"forced_action": "Success", "live_state": bot_state})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
