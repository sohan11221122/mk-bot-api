from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
import threading
import re
import os

app = Flask(__name__)
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

def setup_browser():
    chrome_options = Options()
    # পিসিতে দেখার জন্য headless কমেন্ট করা আছে, Render এ দিলে আনকমেন্ট করবেন
    # chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def run_mk_bot():
    print("🚀 Strict Bot (Only First Row) Started...")
    driver = setup_browser()
    wait = WebDriverWait(driver, 20)
    
    # যে নাম্বারটি নিয়ে কাজ চলছে, তা সেভ করে রাখার জন্য
    current_active_phone = None 
    
    try:
        print("[*] Logging in to MK Network...")
        driver.get("http://mknetworkbd.com/auth.php")
        time.sleep(3)
        
        email_field = wait.until(EC.presence_of_element_located((By.NAME, "phone_email")))
        email_field.clear()
        email_field.send_keys("sohan.shahel.sifa@gmail.com")
        
        pass_field = driver.find_element(By.NAME, "password")
        pass_field.clear()
        pass_field.send_keys("Sohan123@@##")
        
        login_btn = wait.until(EC.element_to_be_clickable((By.ID, "t-btnlog")))
        driver.execute_script("arguments[0].click();", login_btn)
            
        time.sleep(5)
        print("[+] Login Successful!")
        
        driver.get("http://mknetworkbd.com/getnum.php")
        time.sleep(5)

        while True:
            try:
                # 🟢 ১. সিগন্যাল চেক এবং শুধুমাত্র নতুন নাম্বার নেওয়া
                sig_res = requests.get(f"{API_BRIDGE_URL}?action=check_signal", timeout=5).json()
                if sig_res.get("signal") == "GET":
                    print("[*] 🔔 Signal Received! Clicking GET NUMBER for a NEW task...")
                    requests.get(f"{API_BRIDGE_URL}?action=signal_received", timeout=5)
                    
                    target_range = requests.get(f"{API_BRIDGE_URL}?action=get_range", timeout=5).json().get('range', '')
                    if target_range:
                        range_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'XXXXX')]")))
                        range_input.clear()
                        range_input.send_keys(target_range)
                    
                    # GET NUMBER ক্লিক
                    get_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'GET NUMBER')]")
                    driver.execute_script("arguments[0].click();", get_btn)
                    
                    # টেবিল রিফ্রেশ হওয়ার জন্য অপেক্ষা
                    time.sleep(8) 
                    
                    # 🟢 ২. শুধুমাত্র প্রথম রো (Row) থেকে নাম্বার নেওয়া
                    rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                    if rows:
                        first_row = rows[0]
                        cols = first_row.find_elements(By.TAG_NAME, "td")
                        
                        if len(cols) >= 3: 
                            try: phone = cols[0].find_element(By.TAG_NAME, "span").text.strip()
                            except: phone = cols[0].text.strip()
                            
                            phone = re.sub(r'[^0-9]', '', phone) 
                            
                            if phone:
                                current_active_phone = phone # এই নাম্বারটি সেট হয়ে গেল
                                print(f"[+] Fresh Number Extracted: {current_active_phone}")
                                
                                # ডাটাবেসে সেভ করা
                                payload = {"phone": current_active_phone, "status": "PENDING", "otp": "Waiting..."}
                                requests.post(f"{API_BRIDGE_URL}?action=save_number", json=payload, timeout=5)

                # 🟢 ৩. যদি কোনো রানিং নাম্বার থাকে, তবে প্রথম ২৫ লাইনে তার OTP খুঁজবে
                if current_active_phone:
                    rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                    for row in rows[:25]:
                        row_text = row.text.replace(" ", "")
                        
                        # যদি এই রো-তে আমার রানিং নাম্বারটি থাকে
                        if current_active_phone in row_text:
                            cols = row.find_elements(By.TAG_NAME, "td")
                            if len(cols) >= 3:
                                status_text = cols[1].text.strip()
                                
                                otp = "N/A"
                                match = re.search(r'\b\d{4,6}\b', status_text) 
                                if match: 
                                    otp = match.group(0)
                                    
                                current_status = "PENDING"
                                if "SUCCESS" in status_text.upper() or otp != "N/A": 
                                    current_status = "SUCCESS"
                                    print(f"🎯 OTP FOUND for {current_active_phone}: {otp}")
                                    # OTP পেলে কারেন্ট নাম্বার ক্লিয়ার করে দেব, যাতে পরের টাস্কের জন্য রেডি হয়
                                    current_active_phone = None 
                                elif "CANCELED" in status_text.upper() or "EXPIRED" in status_text.upper(): 
                                    current_status = "FAILED"
                                    print(f"❌ Number {current_active_phone} Canceled/Expired.")
                                    current_active_phone = None
                                
                                # ডাটাবেসে আপডেট
                                payload = {"phone": current_active_phone if current_active_phone else row_text, "status": current_status, "otp": otp}
                                try: requests.post(f"{API_BRIDGE_URL}?action=save_number", json=payload, timeout=5)
                                except: pass
                            break # নাম্বার পেয়ে গেলে বা চেক হয়ে গেলে লুপ ব্রেক

            except Exception as inner_e:
                pass
            
            time.sleep(5) 

    except Exception as e:
        print(f"❌ Critical Bot Error: {e}")
    finally:
        driver.quit()

@app.route('/')
def home():
    return jsonify({"status": "Strict MK Network Bot is Running!", "version": "8.0"})

if __name__ == '__main__':
    threading.Thread(target=run_mk_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
