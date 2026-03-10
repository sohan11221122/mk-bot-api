import logging
import time
import requests
import threading
import re
import os
import random
from flask import Flask, jsonify
import cloudscraper

app = Flask(__name__)
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

# 🟢 লাইভ স্ট্যাটাস এবং লগের জন্য ড্যাশবোর্ড
bot_state = {
    "status": "Running",
    "is_logged_in": False,
    "last_signal": "Unknown",
    "last_sync": "Never",
    "action_logs": []
}

def add_log(msg):
    print(msg, flush=True)
    # ব্রাউজারে দেখার জন্য লগ সেভ করে রাখা হচ্ছে
    bot_state["action_logs"].insert(0, f"{time.strftime('%I:%M:%S %p')} - {msg}")
    if len(bot_state["action_logs"]) > 10:
        bot_state["action_logs"].pop()

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
api_session = requests.Session()

def login_to_mk():
    try:
        add_log("Fetching Login Page...")
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
            bot_state["is_logged_in"] = True
            add_log("✅ Login Success!")
        else:
            add_log("❌ Login Failed!")
    except Exception as e:
        add_log(f"Login Error: {e}")

def sync_data():
    try:
        current_time = int(time.time())
        
        sig_req = api_session.get(f"{API_BRIDGE_URL}?action=check_signal&_t={current_time}", headers={"User-Agent": "Render-Bot"}, timeout=15)
        if sig_req.status_code == 200:
            sig_res = sig_req.json()
            bot_state["last_signal"] = sig_res.get("signal", "WAIT")
            
            if bot_state["last_signal"] == "GET":
                add_log("🔔 SIGNAL 'GET' RECEIVED! Requesting number...")
                api_session.get(f"{API_BRIDGE_URL}?action=signal_received&_t={current_time}", timeout=10)
                
                range_req = api_session.get(f"{API_BRIDGE_URL}?action=get_range&_t={current_time}", timeout=10).json()
                target_range = range_req.get('range', '')
                
                # 🟢 FIXED: Missing 'submit' parameter added back!
                num_payload = {"service": "fb", "range": target_range, "getBtn": "1", "submit": "1"} 
                time.sleep(random.uniform(1.0, 2.0))
                scraper.post("http://mknetworkbd.com/getnum.php", data=num_payload, timeout=20)
                add_log(f"📤 Requested new number from MK Network! (Range: {target_range})")

        time.sleep(random.uniform(2.0, 3.0))
        table_res = scraper.get("http://mknetworkbd.com/getnum.php", timeout=20)
        
        if "login" in table_res.url.lower():
            bot_state["is_logged_in"] = False
            add_log("⚠️ Session expired!")
            return

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
            bot_state["last_sync"] = f"Synced {len(bulk_data)} numbers"
        
    except Exception as e:
        add_log(f"Sync Error: {e}")

def background_loop():
    add_log("🚀 Background Thread Started!")
    while True:
        if not bot_state["is_logged_in"]:
            login_to_mk()
            time.sleep(5)
        else:
            sync_data()
            time.sleep(12) 

bot_thread = threading.Thread(target=background_loop, daemon=True)
bot_thread.start()

@app.route('/')
def home():
    return jsonify(bot_state)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
