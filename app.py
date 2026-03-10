from flask import Flask, jsonify
import time
import requests
import threading
import re
import os

app = Flask(__name__)
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

def run_mk_bot():
    print("🚀 Super-Fast Magic API Bot Started...", flush=True)
    
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    while True:
        try:
            print("[*] Fetching Login Page to extract session...", flush=True)
            res = session.get("http://mknetworkbd.com/auth.php", headers=headers, timeout=15)
            html = res.text
            
            inputs = re.findall(r'<input([^>]+)>', html, re.IGNORECASE)
            email_name = "email"
            pass_name = "password"
            
            for inp in inputs:
                inp_lower = inp.lower()
                name_match = re.search(r'name=["\']([^"\']+)["\']', inp, re.IGNORECASE)
                if name_match:
                    if 'type="password"' in inp_lower or "type='password'" in inp_lower:
                        pass_name = name_match.group(1)
                    elif 'type="text"' in inp_lower or 'type="email"' in inp_lower:
                        if 'email' in inp_lower or 'user' in inp_lower or 'phone' in inp_lower:
                            email_name = name_match.group(1)
                            
            print(f"[*] Auto-Detected Fields -> Email: '{email_name}', Password: '{pass_name}'", flush=True)
            
            login_payload = {
                email_name: "sohan.shahel.sifa@gmail.com",
                pass_name: "Sohan123@@##",
                "login": "1",
                "submit": "1",
                "t-btnlog": "1"
            }
            
            print("[*] Sending Login Request...", flush=True)
            login_res = session.post("http://mknetworkbd.com/auth.php", data=login_payload, headers=headers, timeout=15)
            
            if "dashboard" not in login_res.text.lower() and "logout" not in login_res.text.lower():
                print("❌ Login Failed! Retrying in 30s...", flush=True)
                time.sleep(30)
                continue
                
            print("[+] Login OK! Session Secured. Polling for numbers...", flush=True)
            
            loop_count = 0
            while True:
                try:
                    loop_count += 1
                    current_time = int(time.time())
                    
                    # Signal Check with Anti-Cache
                    sig_req_url = f"{API_BRIDGE_URL}?action=check_signal&_t={current_time}"
                    sig_res = session.get(sig_req_url, headers=headers, timeout=10).json()
                    
                    if loop_count % 5 == 0:
                        print(f"[*] Heartbeat: Checking DB Signal... (Current Status: {sig_res.get('signal')})", flush=True)
                    
                    if sig_res.get("signal") == "GET":
                        print("\n🔔 SIGNAL RECEIVED: Desk Bot wants a number!", flush=True)
                        session.get(f"{API_BRIDGE_URL}?action=signal_received&_t={current_time}", headers=headers, timeout=5)
                        
                        target_range = session.get(f"{API_BRIDGE_URL}?action=get_range&_t={current_time}", headers=headers, timeout=5).json().get('range', '')
                        
                        print(f"[*] Requesting new number...", flush=True)
                        num_payload = {"service": "fb", "range": target_range, "getBtn": "1", "submit": "1"} 
                        session.post("http://mknetworkbd.com/getnum.php", data=num_payload, headers=headers, timeout=10)

                    # Bulk OTP Update
                    table_res = session.get("http://mknetworkbd.com/getnum.php", headers=headers, timeout=10)
                    
                    rows = re.findall(r'<tr.*?>(.*?)</tr>', table_res.text, re.DOTALL | re.IGNORECASE)
                    bulk_data = []
                    
                    for row in rows[:25]:
                        cols = re.findall(r'<td.*?>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                        if len(cols) >= 2:
                            raw_phone_text = re.sub(r'<.*?>', ' ', cols[0]) 
                            phone_match = re.search(r'(\d{10,15})', raw_phone_text)
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
                        session.post(f"{API_BRIDGE_URL}?action=save_bulk_numbers", json={"numbers": bulk_data}, timeout=10)
                        
                    time.sleep(3)
                        
                except Exception as inner_e:
                    print(f"[-] Inner Loop Error: {inner_e}", flush=True)
                    time.sleep(5)
                    if "session" in str(inner_e).lower() or "login" in str(inner_e).lower(): 
                        break
                    
        except Exception as e:
            print(f"❌ Critical Error: {e}", flush=True)
            time.sleep(10)

# 🟢 MAGIC FIX: Start the thread globally, outside of __main__ block so Render cannot ignore it!
bot_thread = threading.Thread(target=run_mk_bot, daemon=True)
bot_thread.start()

@app.route('/')
def home():
    return jsonify({"status": "Magic API Bot is Running 🚀", "thread_alive": bot_thread.is_alive()})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
