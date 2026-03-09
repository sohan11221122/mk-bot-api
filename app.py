from flask import Flask, jsonify
import time
import requests
import threading
import re
import os

app = Flask(__name__)
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

def run_mk_bot():
    print("🚀 Super-Fast Magic API Bot Started...")
    
    # সেশন তৈরি করা (যাতে কুকিজ সেভ থাকে)
    session = requests.Session()
    
    # রিয়েল ব্রাউজারের মতো হেডার
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    while True:
        try:
            print("[*] Fetching Login Page to extract session & input names...")
            
            # 🟢 ১. লগইনের আগে পেজ ভিজিট করা
            res = session.get("http://mknetworkbd.com/auth.php", headers=headers, timeout=15)
            html = res.text
            
            # 🟢 ২. Auto-Detect Logic (ইনপুটের নাম নিজে নিজে খুঁজে বের করবে)
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
                            
            print(f"[*] Auto-Detected Fields -> Email: '{email_name}', Password: '{pass_name}'")
            
            # 🟢 ৩. ডাইনামিক পেলোড তৈরি ও লগইন রিকোয়েস্ট
            login_payload = {
                email_name: "sohan.shahel.sifa@gmail.com",
                pass_name: "Sohan123@@##",
                "login": "1",
                "submit": "1",
                "t-btnlog": "1"
            }
            
            print("[*] Sending Login Request...")
            login_res = session.post("http://mknetworkbd.com/auth.php", data=login_payload, headers=headers, timeout=15)
            
            # লগইন সফল হয়েছে কিনা চেক করা
            if "dashboard" not in login_res.text.lower() and "logout" not in login_res.text.lower():
                print("❌ Login Failed! Retrying in 30s...")
                time.sleep(30)
                continue
                
            print("[+] Login OK! Session Secured. Polling for numbers...")
            
            # 🟢 ৪. মেইন লুপ (নাম্বার ও ওটিপি আনা)
            while True:
                try:
                    # Signal Check
                    sig_res = requests.get(f"{API_BRIDGE_URL}?action=check_signal", timeout=10).json()
                    
                    if sig_res.get("signal") == "GET":
                        print("\n🔔 SIGNAL RECEIVED: Desk Bot wants a number!")
                        requests.get(f"{API_BRIDGE_URL}?action=signal_received", timeout=5)
                        
                        target_range = requests.get(f"{API_BRIDGE_URL}?action=get_range", timeout=5).json().get('range', '')
                        
                        print(f"[*] Requesting new number...")
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
                        requests.post(f"{API_BRIDGE_URL}?action=save_bulk_numbers", json={"numbers": bulk_data}, timeout=10)
                        print(f"[*] Synced {len(bulk_data)} numbers with Admin Panel.")
                        
                    time.sleep(3) # ৩ সেকেন্ড পর পর রিফ্রেশ
                        
                except Exception as inner_e:
                    print(f"[-] Inner Loop Error: {inner_e}")
                    time.sleep(5)
                    if "session" in str(inner_e).lower() or "login" in str(inner_e).lower(): 
                        break # সেশন আউট হলে আবার লগইন করবে
                    
        except Exception as e:
            print(f"❌ Critical Error: {e}")
            time.sleep(10)

@app.route('/')
def home():
    return jsonify({"status": "Magic API Bot is Running 🚀"})

if __name__ == '__main__':
    threading.Thread(target=run_mk_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
