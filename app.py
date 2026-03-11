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
    "action_logs": [],
    "last_synced_phone": "",
    "current_signal": "UNKNOWN",
    "total_synced": 0,
    "error_count": 0
}

def add_log(msg, level="INFO"):
    timestamp = time.strftime('%I:%M:%S %p')
    log_entry = f"{timestamp} [{level}] {msg}"
    print(log_entry, flush=True)
    bot_state["action_logs"].insert(0, f"{timestamp} - {msg}")
    if len(bot_state["action_logs"]) > 25:
        bot_state["action_logs"].pop()

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return webdriver.Chrome(options=options)

def send_to_database(phone, otp, status):
    """📤 ডাটাবেসে নম্বর পাঠানো"""
    try:
        payload = {
            "numbers": [{
                "phone": phone,
                "otp": otp,
                "status": status
            }]
        }
        
        add_log(f"📤 Sending to DB: phone={phone}, otp={otp}, status={status}")
        
        response = requests.post(
            f"{API_BRIDGE_URL}?action=save_bulk_numbers",
            json=payload,
            timeout=15
        )
        
        add_log(f"📥 DB Response: HTTP {response.status_code} - {response.text[:150]}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("status") == "success":
                    return True
                else:
                    add_log(f"❌ DB returned error: {data}", "ERROR")
                    return False
            except:
                return True  # Assume success if can't parse JSON
        else:
            add_log(f"❌ HTTP Error: {response.status_code}", "ERROR")
            return False
            
    except Exception as e:
        add_log(f"❌ DB Connection Error: {e}", "ERROR")
        return False

def parse_table_rows(html, target_prefix=""):
    """📊 টেবিল থেকে নম্বর বের করা"""
    results = []
    
    # প্রথমে সব <tr> খুঁজে বের করি
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
    add_log(f"📊 Found {len(rows)} table rows in HTML")
    
    for idx, row in enumerate(rows):
        # প্রতিটি row থেকে <td> বের করি
        cols = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
        
        if len(cols) < 1:
            continue
        
        # 🎯 নম্বর বের করার একাধিক পদ্ধতি
        phone = None
        
        # পদ্ধতি ১: প্রথম td থেকে
        col0_text = re.sub(r'<[^>]+>', '', cols[0]).strip()
        
        # বিভিন্ন pattern দিয়ে নম্বর খোঁজা
        patterns = [
            r'(880\d{10})',      # 880 দিয়ে শুরু
            r'(\d{13})',         # 13 digit
            r'(\d{11,15})',      # 11-15 digit
        ]
        
        for pattern in patterns:
            match = re.search(pattern, col0_text)
            if match:
                phone = match.group(1)
                break
        
        # পদ্ধতি ২: পুরো td HTML থেকে
        if not phone:
            for pattern in patterns:
                match = re.search(pattern, cols[0])
                if match:
                    phone = match.group(1)
                    break
        
        if not phone:
            continue
            
        # 🎯 Prefix check (যদি দেওয়া থাকে)
        if target_prefix:
            clean_prefix = target_prefix.replace("X", "").replace("x", "")
            if clean_prefix and not phone.startswith(clean_prefix):
                add_log(f"   ⏭️ Skipped {phone} (prefix mismatch, need {clean_prefix})")
                continue
        
        # 🎯 OTP এবং Status বের করা
        otp = "N/A"
        status = "PENDING"
        
        if len(cols) > 1:
            col1_text = re.sub(r'<[^>]+>', '', cols[1]).strip()
            
            # OTP খোঁজা
            otp_match = re.search(r'\b(\d{4,6})\b', col1_text)
            if otp_match:
                otp = otp_match.group(1)
            
            # Status চেক
            col1_upper = col1_text.upper()
            if "SUCCESS" in col1_upper or otp != "N/A":
                status = "SUCCESS"
            elif any(x in col1_upper for x in ["CANCEL", "EXPIRED", "FAILED", "TIMEOUT"]):
                status = "FAILED"
        
        results.append({
            "phone": phone,
            "otp": otp,
            "status": status,
            "row_index": idx
        })
        
        add_log(f"✅ Parsed: {phone} | OTP: {otp} | Status: {status}")
    
    return results

def background_loop():
    add_log("🚀 MK Network Bot Started!")
    add_log(f"🔗 API Bridge: {API_BRIDGE_URL}")
    
    # শুরুতে API চেক
    try:
        r = requests.get(f"{API_BRIDGE_URL}?action=check_signal", timeout=10)
        add_log(f"✅ API Bridge connected: {r.text[:100]}")
    except Exception as e:
        add_log(f"❌ API Bridge failed: {e}", "ERROR")
    
    while True:
        driver = None
        try:
            add_log("=" * 50)
            add_log("🌐 Opening browser...")
            driver = create_driver()
            wait = WebDriverWait(driver, 20)
            
            # ===== লগইন =====
            add_log("🔐 Logging into MK Network...")
            driver.get("http://mknetworkbd.com/auth.php")
            time.sleep(3)
            
            # Email field
            email_found = False
            for xpath in ["//input[@type='text']", "//input[contains(@placeholder,'email')]", "//input[contains(@placeholder,'phone')]", "//input[@name='email']", "//input[@name='phone']"]:
                try:
                    elem = driver.find_element(By.XPATH, xpath)
                    elem.clear()
                    elem.send_keys(EMAIL)
                    email_found = True
                    add_log(f"✅ Email entered via: {xpath}")
                    break
                except:
                    continue
            
            if not email_found:
                add_log("❌ Email field not found!", "ERROR")
                bot_state["error_count"] += 1
                driver.quit()
                time.sleep(10)
                continue
            
            # Password field
            pass_found = False
            for xpath in ["//input[@type='password']", "//input[contains(@placeholder,'password')]", "//input[@name='password']"]:
                try:
                    elem = driver.find_element(By.XPATH, xpath)
                    elem.clear()
                    elem.send_keys(PASSWORD)
                    pass_found = True
                    add_log(f"✅ Password entered")
                    break
                except:
                    continue
            
            if not pass_found:
                add_log("❌ Password field not found!", "ERROR")
                driver.quit()
                time.sleep(10)
                continue
            
            time.sleep(1)
            
            # Login button
            for xpath in ["//button[@type='submit']", "//button[contains(text(),'Login')]", "//form//button", "//input[@type='submit']"]:
                try:
                    btn = driver.find_element(By.XPATH, xpath)
                    driver.execute_script("arguments[0].click();", btn)
                    add_log("✅ Login button clicked")
                    break
                except:
                    continue
            
            time.sleep(5)
            
            # Login check
            if "auth.php" in driver.current_url:
                add_log("❌ Login failed - still on auth page", "ERROR")
                driver.quit()
                time.sleep(15)
                continue
            
            add_log("✅ Login successful!")
            
            # Get Number page এ যাওয়া
            driver.get("http://mknetworkbd.com/getnum.php")
            time.sleep(4)
            
            # ===== Main Loop =====
            while True:
                current_time = int(time.time())
                
                # Session check
                if "auth.php" in driver.current_url:
                    add_log("⚠️ Session expired - re-login needed")
                    break
                
                # 🔔 Signal check
                try:
                    sig_response = requests.get(
                        f"{API_BRIDGE_URL}?action=check_signal&_t={current_time}",
                        timeout=10
                    )
                    sig_data = sig_response.json()
                    signal = sig_data.get("signal", "WAIT")
                    bot_state["current_signal"] = signal
                except Exception as e:
                    add_log(f"⚠️ Signal check error: {e}", "WARN")
                    signal = "WAIT"
                
                # Range check
                live_range = ""
                try:
                    range_response = requests.get(
                        f"{API_BRIDGE_URL}?action=get_range&_t={current_time}",
                        timeout=10
                    )
                    range_data = range_response.json()
                    live_range = range_data.get("range", "")
                except:
                    pass
                
                # 🎯 GET signal পেলে নম্বর রিকোয়েস্ট করবে
                if signal == "GET":
                    add_log(f"🔔 SIGNAL=GET received! Range: {live_range}")
                    
                    # Range input
                    if live_range:
                        for xpath in ["//input[@name='range']", "//input[@type='text']", "//form//input[1]"]:
                            try:
                                inp = driver.find_element(By.XPATH, xpath)
                                inp.clear()
                                inp.send_keys(live_range)
                                add_log(f"✅ Range set: {live_range}")
                                break
                            except:
                                continue
                        time.sleep(1)
                    
                    # Get Number button click
                    add_log("🖱️ Clicking Get Number button...")
                    btn_clicked = False
                    for xpath in [
                        "//button[contains(text(),'Get Number')]",
                        "//button[contains(text(),'GET NUMBER')]",
                        "//button[contains(text(),'Get')]",
                        "//button[contains(@class,'btn')]",
                        "//a[contains(text(),'Get')]",
                        "//input[@value='Get Number']"
                    ]:
                        try:
                            btn = driver.find_element(By.XPATH, xpath)
                            driver.execute_script("arguments[0].click();", btn)
                            add_log(f"✅ Clicked button via: {xpath[:40]}...")
                            btn_clicked = True
                            break
                        except:
                            continue
                    
                    if not btn_clicked:
                        add_log("⚠️ Could not find Get Number button", "WARN")
                    
                    time.sleep(3)
                    
                    # Alert handle
                    try:
                        alert = driver.switch_to.alert
                        add_log(f"⚠️ Alert: {alert.text[:50]}")
                        alert.accept()
                    except:
                        pass
                    
                    # Page reload
                    add_log("🔄 Reloading page...")
                    time.sleep(5)
                    driver.get("http://mknetworkbd.com/getnum.php")
                    time.sleep(8)
                    
                    # Signal received confirmation
                    try:
                        requests.get(f"{API_BRIDGE_URL}?action=signal_received&_t={current_time}", timeout=5)
                    except:
                        pass
                
                # 📊 Table পড়া
                add_log("📊 Reading table...")
                html = driver.page_source
                
                target_prefix = live_range.replace("X", "").replace("x", "") if live_range else ""
                numbers = parse_table_rows(html, target_prefix)
                
                # 📤 ডাটাবেসে পাঠানো
                if numbers:
                    for num_data in numbers:
                        phone = num_data["phone"]
                        
                        # Duplicate check
                        if phone == bot_state.get("last_synced_phone"):
                            add_log(f"⏭️ Skipping duplicate: {phone}")
                            continue
                        
                        # ডাটাবেসে পাঠানো
                        success = send_to_database(
                            phone,
                            num_data["otp"],
                            num_data["status"]
                        )
                        
                        if success:
                            bot_state["last_synced_phone"] = phone
                            bot_state["total_synced"] += 1
                            bot_state["status"] = f"🟢 Active | Last: {phone}"
                            add_log(f"✅ SUCCESS: {phone} saved to DB!")
                        else:
                            add_log(f"❌ FAILED: {phone} not saved", "ERROR")
                            bot_state["error_count"] += 1
                        
                        break  # প্রথম নম্বর নিয়েই ব্রেক
                else:
                    add_log("📭 No valid numbers in table")
                
                time.sleep(10)
                
        except Exception as e:
            add_log(f"❌ Error: {e}", "ERROR")
            bot_state["error_count"] += 1
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            time.sleep(5)

# Start background thread
bot_thread = threading.Thread(target=background_loop, daemon=True)
bot_thread.start()

@app.route('/')
def home():
    return jsonify(bot_state)

@app.route('/status')
def status():
    return jsonify({
        "status": bot_state["status"],
        "signal": bot_state["current_signal"],
        "total_synced": bot_state["total_synced"],
        "errors": bot_state["error_count"]
    })

@app.route('/logs')
def logs():
    return jsonify({"logs": bot_state["action_logs"]})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
