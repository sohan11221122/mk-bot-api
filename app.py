from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
import time
import requests
import re
import os

app = Flask(__name__)

# 🟢 কনফিগারেশন
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"
EMAIL = "sohan.shahel.sifa@gmail.com"
PASSWORD = "Sohan123@@##"

# 🟢 লাইভ ড্যাশবোর্ড স্ট্যাটাস
bot_state = {
    "status": "Initializing System...",
    "action_logs": []
}

def add_log(msg):
    print(msg, flush=True)
    bot_state["action_logs"].insert(0, f"{time.strftime('%I:%M:%S %p')} - {msg}")
    if len(bot_state["action_logs"]) > 15:
        bot_state["action_logs"].pop()

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    return webdriver.Chrome(options=options)

def background_loop():
    add_log("🚀 Background System Started!")
    
    while True:
        driver = None
        try:
            add_log("[*] Opening Virtual Browser...")
            driver = create_driver()
            wait = WebDriverWait(driver, 15)
            
            # --- ১. লগইন প্রসেস ---
            add_log("[*] Logging into MK Network...")
            driver.get("http://mknetworkbd.com/auth.php")
            
            email_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'phone or email') or @type='text']")))
            pass_field = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'password') or @type='password']")
            
            email_field.clear()
            email_field.send_keys(EMAIL)
            pass_field.clear()
            pass_field.send_keys(PASSWORD)
            time.sleep(1)
            
            try:
                login_btn = driver.find_element(By.XPATH, "/html/body/div[1]/div[4]/form/button")
                driver.execute_script("arguments[0].click();", login_btn)
            except:
                pass_field.submit()
            
            time.sleep(5)
            if "auth.php" in driver.current_url:
                add_log("❌ Login failed. Retrying in 10s...")
                driver.quit()
                time.sleep(10)
                continue
                
            add_log("✅ Login Success!")
            driver.get("http://mknetworkbd.com/getnum.php")
            time.sleep(3)

            # --- ২. Main Monitor Loop ---
            while True:
                current_time = int(time.time())
                
                # 🛡️ Auto-Login Check 1
                if "auth.php" in driver.current_url:
                    add_log("⚠️ Session Expired! Triggering Auto Re-Login...")
                    break 
                
                sig_req = requests.get(f"{API_BRIDGE_URL}?action=check_signal&_t={current_time}", timeout=10)
                
                if sig_req.status_code == 200 and sig_req.json().get("signal") == "GET":
                    add_log("🔔 SIGNAL 'GET' RECEIVED!")
                    requests.get(f"{API_BRIDGE_URL}?action=signal_received&_t={current_time}", timeout=10)
                    
                    # 🎯 ডায়নামিক রেঞ্জ
                    live_range = ""
                    try:
                        range_data = requests.get(f"{API_BRIDGE_URL}?action=get_range&_t={current_time}", timeout=10).json()
                        live_range = range_data.get('range', '')
                    except:
                        pass
                    
                    if live_range:
                        try:
                            range_input = driver.find_element(By.XPATH, "//input[@name='range' or @type='text']")
                            range_input.clear()
                            range_input.send_keys(live_range)
                            add_log(f"[*] Range set to: {live_range}")
                            time.sleep(1)
                        except:
                            pass

                    # 🖱️ Get Number Click
                    add_log("[*] Requesting 1 new number...")
                    try:
                        btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'get number')]")))
                        driver.execute_script("arguments[0].click();", btn)
                        
                        # 🟢 5s Wait -> Refresh -> 8s Wait for Table
                        add_log("[*] Waiting 5s then Refreshing page...")
                        time.sleep(5)
                        driver.refresh()
                        
                        add_log("[*] Waiting 8s for table to load properly...")
                        time.sleep(8)
                        
                        # 🛡️ Auto-Login Check 2 
                        if "auth.php" in driver.current_url:
                            add_log("⚠️ Logged out after refresh! Triggering Auto Re-Login...")
                            break
                            
                    except Exception as e:
                        add_log(f"   -> Click/Refresh error: {e}")
                
                # 📊 টেবিল রিড করা
                html = driver.page_source
                rows = re.findall(r'<tr.*?>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
                bulk_data = []

                # 🟢 "rows[:5]" করা হয়েছে যাতে পেন্ডিং নাম্বার জমে থাকলেও সে মিস না করে
                for row in rows[:5]:
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

                # 📤 ডাটাবেসে সেভ করা (with Live Tracker)
                if bulk_data:
                    add_log(f"[*] Found {len(bulk_data)} numbers in table! Sending to DB...")
                    try:
                        db_res = requests.post(f"{API_BRIDGE_URL}?action=save_bulk_numbers", json={"numbers": bulk_data}, timeout=15)
                        if db_res.status_code == 200:
                            add_log("✅ Successfully saved to Database!")
                        else:
                            add_log(f"❌ DB Blocked the request! HTTP Status: {db_res.status_code}")
                            
                        bot_state["status"] = f"🟢 Active | Last Synced: {bulk_data[0].get('phone')}..."
                    except Exception as e:
                        add_log(f"❌ Failed to connect to DB: {e}")
                else:
                    # 🟢 যদি নাম্বার না পায়, সেটা লগে দেখাবে
                    if sig_req.status_code == 200 and sig_req.json().get("signal") == "GET":
                         add_log("⚠️ No numbers found in the table after refresh!")
                
                time.sleep(10) 
                
        except Exception as e:
            add_log(f"⚠️ System Error: {e}")
        finally:
            if driver:
                driver.quit() 
            time.sleep(5) 

bot_thread = threading.Thread(target=background_loop, daemon=True)
bot_thread.start()

@app.route('/')
def home():
    return jsonify(bot_state)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
