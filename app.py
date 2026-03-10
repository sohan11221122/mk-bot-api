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
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"
EMAIL = "sohan.shahel.sifa@gmail.com"
PASSWORD = "Sohan123@@##"
TARGET_RANGE = "237629XXXXXX"

# লাইভ ড্যাশবোর্ড
bot_state = {
    "status": "Starting Server Browser...",
    "action_logs": []
}

def add_log(msg):
    print(msg, flush=True)
    bot_state["action_logs"].insert(0, f"{time.strftime('%I:%M:%S %p')} - {msg}")
    if len(bot_state["action_logs"]) > 15:
        bot_state["action_logs"].pop()

def create_driver():
    # 🟢 সার্ভারের জন্য Headless (অদৃশ্য) মোড চালু করা
    options = webdriver.ChromeOptions()
    options.add_argument('--headless') # ব্যাকগ্রাউন্ডে চলবে
    options.add_argument('--no-sandbox') # লিনাক্স সার্ভারের জন্য জরুরি
    options.add_argument('--disable-dev-shm-usage') # মেমোরি ক্র্যাশ ঠেকানোর জন্য
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    return webdriver.Chrome(options=options)

def background_loop():
    add_log("🚀 Background Browser Thread Started!")
    
    while True: # যদি ব্রাউজার ক্র্যাশ করে, তবে আবার নতুন করে শুরু হবে
        driver = None
        try:
            add_log("[*] Initializing Chrome Browser...")
            driver = create_driver()
            wait = WebDriverWait(driver, 15)
            
            # --- 1. Login ---
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
            
            # --- 2. Setup Page & Range ---
            driver.get("http://mknetworkbd.com/getnum.php")
            time.sleep(3)
            try:
                range_input = driver.find_element(By.XPATH, "//input[@name='range' or @type='text']")
                range_input.clear()
                range_input.send_keys(TARGET_RANGE)
                add_log(f"[*] Range set to: {TARGET_RANGE}")
            except:
                pass

            # --- 3. Main Monitor Loop ---
            while True:
                current_time = int(time.time())
                
                # Signal Check from DB
                sig_req = requests.get(f"{API_BRIDGE_URL}?action=check_signal&_t={current_time}", timeout=10)
                if sig_req.status_code == 200 and sig_req.json().get("signal") == "GET":
                    add_log("🔔 SIGNAL 'GET' RECEIVED!")
                    requests.get(f"{API_BRIDGE_URL}?action=signal_received&_t={current_time}", timeout=10)
                    
                    # Click Button
                    add_log("[*] Requesting new numbers from site...")
                    for i in range(2):
                        try:
                            btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'get number')]")))
                            driver.execute_script("arguments[0].click();", btn)
                            time.sleep(4)
                        except Exception as e:
                            add_log(f"   -> Click error: {e}")
                
                # Read Table & OTPs
                html = driver.page_source
                rows = re.findall(r'<tr.*?>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
                bulk_data = []

                for row in rows[:8]:
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
                    requests.post(f"{API_BRIDGE_URL}?action=save_bulk_numbers", json={"numbers": bulk_data}, timeout=10)
                    bot_state["status"] = f"Synced {len(bulk_data)} numbers"
                
                time.sleep(12) # লুপের গ্যাপ
                
        except Exception as e:
            add_log(f"⚠️ Critical Error: {e}")
            if driver:
                driver.quit()
            time.sleep(10) # ক্র্যাশ করলে ১০ সেকেন্ড পর ব্রাউজার রিস্টার্ট হবে

bot_thread = threading.Thread(target=background_loop, daemon=True)
bot_thread.start()

@app.route('/')
def home():
    return jsonify(bot_state)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
