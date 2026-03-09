from flask import Flask, jsonify
import time
import requests
import threading
import re
import os

app = Flask(__name__)
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

def run_mk_bot():
    print("🚀 Super-Fast API Bot Started (No Browser!)...")
    
    # সেশন তৈরি করা (যাতে লগইন কুকিজ সেভ থাকে)
    session = requests.Session()
    
    # সাধারণ ইউজারের মতো সাজার জন্য হেডার
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    
    while True:
        try:
            print("[*] Attempting to login via API...")
            
            # ⚠️ আপনার সাইটের লগইন ফর্মের ইনপুট নামগুলো (name="...") এখানে দিতে হবে
            # সাধারণত email এবং password বা pass থাকে। 
            login_payload = {
                "email": "sohan.shahel.sifa@gmail.com", 
                "password": "Sohan123@@##",
                "login": "1" # লগইন বাটনের ভ্যালু (যদি থাকে)
            }
            
            # লগইন রিকোয়েস্ট পাঠানো
            login_res = session.post("http://mknetworkbd.com/auth.php", data=login_payload, headers=headers, timeout=15)
            
            # লগইন সফল হয়েছে কিনা চেক করা
            if "login" in login_res.url.lower() or "invalid" in login_res.text.lower():
                print("❌ Login Failed! Password/Email wrong or Payload names don't match. Retrying in 30s...")
                time.sleep(30)
                continue
                
            print("[+] Login OK! Session Secured. Polling for numbers...")
            
            while True:
                try:
                    # 🟢 ১. Signal Check (ডেস্কটপ থেকে নাম্বার চাইছে কিনা)
                    sig_res = requests.get(f"{API_BRIDGE_URL}?action=check_signal", timeout=10).json()
                    
                    if sig_res.get("signal") == "GET":
                        print("\n🔔 SIGNAL RECEIVED: Desk Bot wants a number!")
                        requests.get(f"{API_BRIDGE_URL}?action=signal_received", timeout=5)
                        
                        target_range = requests.get(f"{API_BRIDGE_URL}?action=get_range", timeout=5).json().get('range', '')
                        
                        # নতুন নাম্বারের জন্য রিকোয়েস্ট (Get Number Button Click এর বিকল্প)
                        print(f"[*] Requesting new number...")
                        # ⚠️ সাইটে Get Number বাটনে ক্লিক করলে যে রিকোয়েস্ট যায়, সেটা এখানে দিতে হবে
                        num_payload = {"service": "fb", "range": target_range} 
                        session.post("http://mknetworkbd.com/getnum.php", data=num_payload, headers=headers, timeout=10)

                    # 🟢 ২. Bulk OTP Update (Table থেকে ডেটা পড়া)
                    table_res = session.get("http://mknetworkbd.com/getnum.php", headers=headers, timeout=10)
                    
                    # HTML টেবিল থেকে Regex দিয়ে নাম্বার ও OTP আলাদা করা
                    rows = re.findall(r'<tr.*?>(.*?)</tr>', table_res.text, re.DOTALL | re.IGNORECASE)
                    bulk_data = []
                    
                    for row in rows[:25]:
                        cols = re.findall(r'<td.*?>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                        if len(cols) >= 2:
                            # নাম্বার বের করা
                            raw_phone_text = re.sub(r'<.*?>', ' ', cols[0]) # HTML ট্যাগ মুছে ফেলা
                            phone_match = re.search(r'(\d{10,15})', raw_phone_text)
                            if not phone_match: continue
                            phone = phone_match.group(1)
                            
                            # স্ট্যাটাস ও OTP বের করা
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
                        
                    time.sleep(3) # প্রতি ৩ সেকেন্ডে সাইট রিফ্রেশ করবে
                        
                except Exception as inner_e:
                    print(f"[-] Inner Loop Error: {inner_e}")
                    time.sleep(5)
                    if "session" in str(inner_e).lower(): break # সেশন আউট হলে আবার লগইন করবে
                    
        except Exception as e:
            print(f"❌ Critical Error: {e}")
            time.sleep(10)

@app.route('/')
def home():
    return jsonify({"status": "Fast API Bot is Running 🚀", "mode": "Requests Module"})

if __name__ == '__main__':
    threading.Thread(target=run_mk_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
