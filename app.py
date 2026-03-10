from flask import Flask, jsonify
import time
import requests
import threading
import re
import os
import sys

# 🟢 Force Python to show logs immediately on Render
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

def run_mk_bot():
    print("🚀 [START] Super-Fast Magic API Bot Initialized!", flush=True)
    
    # 🟢 দুটি আলাদা সেশন (যাতে MK Network আর AwardSpace এর কুকিজ মিক্স না হয়)
    session = requests.Session() 
    api_session = requests.Session() 
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    while True:
        try:
            print("⏳ [1] Fetching MK Network Login Page...", flush=True)
            res = session.get("http://mknetworkbd.com/auth.php", headers=headers, timeout=15)
            
            email_name, pass_name = "email", "password"
            inputs = re.findall(r'<input([^>]+)>', res.text, re.IGNORECASE)
            for inp in inputs:
                name_match = re.search(r'name=["\']([^"\']+)["\']', inp, re.IGNORECASE)
                if name_match:
                    inp_lower = inp.lower()
                    if 'password' in inp_lower: pass_name = name_match.group(1)
                    elif 'email' in inp_lower or 'user' in inp_lower: email_name = name_match.group(1)
                            
            print(f"🔑 [2] Extracted Fields -> {email_name}, {pass_name}. Sending Login POST...", flush=True)
            
            login_payload = {
                email_name: "sohan.shahel.sifa@gmail.com",
                pass_name: "Sohan123@@##",
                "login": "1", "submit": "1", "t-btnlog": "1"
            }
            
            login_res = session.post("http://mknetworkbd.com/auth.php", data=login_payload, headers=headers, timeout=15)
            
            if "dashboard" not in login_res.text.lower() and "logout" not in login_res.text.lower():
                print("❌ [ERROR] Login Failed! Retrying in 10s...", flush=True)
                time.sleep(10)
                continue
                
            print("✅ [3] Login Success! Entering Main Loop...", flush=True)
            
            while True:
                try:
                    current_time = int(time.time())
                    print(f"🔄 [LOOP] Checking DB Signal at {current_time}...", flush=True)
                    
                    # 🟢 Signal Check from AwardSpace
                    sig_url = f"{API_BRIDGE_URL}?action=check_signal&_t={current_time}"
                    sig_req = api_session.get(sig_url, headers={"User-Agent": "RenderCloud/2.0"}, timeout=10)
                    
                    if sig_req.status_code != 200:
                        print(f"⚠️ [API ERROR] AwardSpace blocked request. HTTP Code: {sig_req.status_code}", flush=True)
                        time.sleep(5)
                        continue
                        
                    sig_res = sig_req.json()
                    print(f"📡 Signal Status: {sig_res.get('signal')}", flush=True)
                    
                    if sig_res.get("signal") == "GET":
                        print("🔔 [ACTION] SIGNAL RECEIVED! Fetching new number...", flush=True)
                        
                        api_session.get(f"{API_BRIDGE_URL}?action=signal_received&_t={current_time}", timeout=5)
                        range_req = api_session.get(f"{API_BRIDGE_URL}?action=get_range&_t={current_time}", timeout=5).json()
                        target_range = range_req.get('range', '')
                        
                        num_payload = {"service": "fb", "range": target_range, "getBtn": "1", "submit": "1"} 
                        session.post("http://mknetworkbd.com/getnum.php", data=num_payload, headers=headers, timeout=10)
                        print("✅ [MK] Number requested from MK Network.", flush=True)

                    print("🔍 [MK] Reading Table for Live Numbers/OTPs...", flush=True)
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
                        print(f"📤 [DB] Syncing {len(bulk_data)} numbers to AwardSpace...", flush=True)
                        api_session.post(f"{API_BRIDGE_URL}?action=save_bulk_numbers", json={"numbers": bulk_data}, timeout=10)
                        
                    print("💤 [SLEEP] Waiting 3 seconds...\n", flush=True)
                    time.sleep(3)
                        
                except Exception as inner_e:
                    print(f"⚠️ [LOOP ERROR] Something went wrong: {inner_e}", flush=True)
                    time.sleep(5)
                    if "json" in str(inner_e).lower() or "decode" in str(inner_e).lower():
                        print("🚨 AwardSpace API returned HTML instead of JSON. IP might be blocked!", flush=True)
                    
        except Exception as e:
            print(f"❌ [CRITICAL ERROR] Bot crashed: {e}", flush=True)
            time.sleep(10)

# 🟢 Start thread outside main block
bot_thread = threading.Thread(target=run_mk_bot, daemon=True)
bot_thread.start()

@app.route('/')
def home():
    return jsonify({"status": "Magic API Bot is Running 🚀", "thread_alive": bot_thread.is_alive()})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
