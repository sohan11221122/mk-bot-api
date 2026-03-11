from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
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
    "debug_info": {}  # 🆕 ডিবাগ ইনফো
}

def add_log(msg, level="INFO"):
    timestamp = time.strftime('%I:%M:%S %p')
    print(f"[{level}] {msg}", flush=True)
    bot_state["action_logs"].insert(0, f"{timestamp} - {msg}")
    if len(bot_state["action_logs"]) > 20:
        bot_state["action_logs"].pop()

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 🆕 এরর লগ এনাবল করা
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    return webdriver.Chrome(options=options)

def check_api_connection():
    """🆕 API Bridge কানেকশন চেক"""
    try:
        response = requests.get(f"{API_BRIDGE_URL}?action=test", timeout=10)
        add_log(f"✅ API Bridge Response: {response.status_code}")
        return True
    except Exception as e:
        add_log(f"❌ API Bridge Connection Failed: {e}", "ERROR")
        return False

def try_multiple_xpaths(driver, xpaths, description="element"):
    """🆕 একাধিক XPath ট্রাই করা"""
    for xpath in xpaths:
        try:
            element = driver.find_element(By.XPATH, xpath)
            add_log(f"✅ Found {description} with XPath: {xpath[:50]}...")
            return element
        except:
            continue
    add_log(f"❌ Could not find {description}", "WARN")
    return None

def background_loop():
    add_log("🚀 Background System Started (Debug Version)!")
    
    # 🆕 শুরুতে API চেক
    check_api_connection()
    
    while True:
        driver = None
        try:
            add_log("[*] Opening Virtual Browser...")
            driver = create_driver()
            wait = WebDriverWait(driver, 20)
            
            # --- ১. লগইন প্রসেস ---
            add_log("[*] Logging into MK Network...")
            driver.get("http://mknetworkbd.com/auth.php")
            time.sleep(3)
            
            # 🆕 একাধিক XPath দিয়ে ইমেইল ফিল্ড খোঁজা
            email_xpaths = [
                "//input[contains(@placeholder, 'phone') or contains(@placeholder, 'email')]",
                "//input[@type='text']",
                "//input[@name='email']",
                "//input[@name='phone']",
                "//input[contains(@class, 'form-control')][1]"
            ]
            
            email_field = try_multiple_xpaths(driver, email_xpaths, "email field")
            if not email_field:
                add_log("❌ Email field not found! Checking page source...", "ERROR")
                bot_state["debug_info"]["page_source_snippet"] = driver.page_source[:1000]
                driver.quit()
                time.sleep(10)
                continue
            
            # 🆕 একাধিক XPath দিয়ে পাসওয়ার্ড ফিল্ড খোঁজা
            pass_xpaths = [
                "//input[@type='password']",
                "//input[contains(@placeholder, 'password')]",
                "//input[@name='password']",
                "//input[contains(@class, 'password')]"
            ]
            
            pass_field = try_multiple_xpaths(driver, pass_xpaths, "password field")
            if not pass_field:
                add_log("❌ Password field not found!", "ERROR")
                driver.quit()
                time.sleep(10)
                continue
            
            email_field.clear()
            email_field.send_keys(EMAIL)
            pass_field.clear()
            pass_field.send_keys(PASSWORD)
            add_log(f"[*] Entered credentials: {EMAIL[:10]}...")
            time.sleep(2)
            
            # 🆕 একাধিক XPath দিয়ে লগইন বাটন খোঁজা
            login_xpaths = [
                "//button[@type='submit']",
                "//button[contains(text(), 'Login') or contains(text(), 'login')]",
                "//input[@type='submit']",
                "//button[contains(@class, 'btn-primary')]",
                "//form//button",
                "/html/body/div[1]/div[4]/form/button"
            ]
            
            login_btn = try_multiple_xpaths(driver, login_xpaths, "login button")
            if login_btn:
                driver.execute_script("arguments[0].click();", login_btn)
                add_log("[*] Clicked login button")
            else:
                add_log("[*] Trying to submit form via password field")
                pass_field.submit()
            
            time.sleep(5)
            
            if "auth.php" in driver.current_url:
                add_log("❌ Login failed! Still on auth page", "ERROR")
                # 🆕 স্ক্রিনশট সেভ (ডিবাগের জন্য)
                try:
                    driver.save_screenshot("/tmp/login_failed.png")
                    add_log("📸 Screenshot saved: /tmp/login_failed.png")
                except:
                    pass
                driver.quit()
                time.sleep(10)
                continue
                
            add_log("✅ Login Success!")
            driver.get("http://mknetworkbd.com/getnum.php")
            time.sleep(4)

            # --- ২. Main Monitor Loop ---
            while True:
                current_time = int(time.time())
                
                # 🛡️ Auto-Login Check
                if "auth.php" in driver.current_url:
                    add_log("⚠️ Session Expired! Triggering Auto Re-Login...")
                    break 
                
                # 🔔 Signal Check
                try:
                    sig_req = requests.get(f"{API_BRIDGE_URL}?action=check_signal&_t={current_time}", timeout=10)
                    sig_data = sig_req.json() if sig_req.status_code == 200 else {}
                except Exception as e:
                    add_log(f"⚠️ Signal check failed: {e}", "WARN")
                    sig_data = {}
                
                signal = sig_data.get("signal", "")
                
                if signal == "GET":
                    add_log("🔔 SIGNAL 'GET' RECEIVED!")
                    
                    # সিগন্যাল রিসিভড কনফার্মেশন
                    try:
                        requests.get(f"{API_BRIDGE_URL}?action=signal_received&_t={current_time}", timeout=10)
                    except:
                        pass
                    
                    # 🎯 ডায়নামিক রেঞ্জ
                    live_range = ""
                    try:
                        range_data = requests.get(f"{API_BRIDGE_URL}?action=get_range&_t={current_time}", timeout=10).json()
                        live_range = range_data.get('range', '')
                        add_log(f"[*] Received range: {live_range}")
                    except Exception as e:
                        add_log(f"⚠️ Could not get range: {e}", "WARN")
                    
                    if live_range:
                        try:
                            range_xpaths = [
                                "//input[@name='range']",
                                "//input[@type='text']",
                                "//input[contains(@placeholder, 'range')]",
                                "//form//input[1]"
                            ]
                            range_input = try_multiple_xpaths(driver, range_xpaths, "range input")
                            if range_input:
                                range_input.clear()
                                range_input.send_keys(live_range)
                                add_log(f"✅ Range set to: {live_range}")
                                time.sleep(1)
                        except Exception as e:
                            add_log(f"⚠️ Range input error: {e}", "WARN")

                    # 🖱️ Get Number Click - 🆕 উন্নত XPath
                    add_log("[*] Requesting 1 new number...")
                    try:
                        btn_xpaths = [
                            "//button[contains(text(), 'Get Number')]",
                            "//button[contains(text(), 'GET NUMBER')]",
                            "//button[contains(text(), 'Get')]",
                            "//button[contains(@class, 'btn') and contains(text(), 'Get')]",
                            "//a[contains(text(), 'Get Number')]",
                            "//input[@value='Get Number']",
                            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'get number')]",
                            "//button[contains(@onclick, 'get')]"
                        ]
                        
                        btn = try_multiple_xpaths(driver, btn_xpaths, "Get Number button")
                        if btn:
                            driver.execute_script("arguments[0].click();", btn)
                            add_log("✅ Clicked Get Number button!")
                            time.sleep(3)
                        else:
                            add_log("❌ Get Number button not found!", "ERROR")
                        
                        # 🟢 Alert Bypass
                        try:
                            alert = driver.switch_to.alert
                            alert_text = alert.text
                            add_log(f"⚠️ Alert detected: {alert_text[:50]}")
                            alert.accept()
                        except:
                            pass
                        
                        add_log("[*] Waiting 5s then reloading page...")
                        time.sleep(5)
                        driver.get("http://mknetworkbd.com/getnum.php") 
                        
                        add_log("[*] Waiting 8s for table to load...")
                        time.sleep(8)
                        
                        if "auth.php" in driver.current_url:
                            add_log("⚠️ Logged out after reload! Re-login needed...")
                            break
                            
                    except Exception as e:
                        add_log(f"❌ Click/Reload error: {e}", "ERROR")
                
                # 📊 টেবিল রিড করা - 🆕 উন্নত পার্সিং
                add_log("[*] Reading table data...")
                html = driver.page_source
                
                # 🆕 ডিবাগ: টেবিল কতগুলো row আছে
                all_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
                add_log(f"[*] Found {len(all_rows)} table rows")
                
                bulk_data = []
                target_prefix = ""
                if live_range:
                    target_prefix = live_range.upper().replace("X", "")
                    add_log(f"[*] Target prefix: {target_prefix}")

                for idx, row in enumerate(all_rows):
                    cols = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                    if len(cols) < 2:
                        continue
                    
                    # 🆕 প্রথম column থেকে নম্বর বের করা
                    raw_phone = re.sub(r'<[^>]+>', '', cols[0]).strip()
                    phone_match = re.search(r'(\d{10,15})', raw_phone)
                    
                    if not phone_match:
                        # 🆕 বিকল্প: লিংক থেকে নম্বর বের করা
                        phone_match = re.search(r'(\d{10,15})', cols[0])
                    
                    if not phone_match:
                        continue
                    
                    phone = phone_match.group(1)
                    add_log(f"[*] Row {idx}: Found phone {phone}")

                    # 🟢 Range Check
                    if target_prefix and not phone.startswith(target_prefix):
                        add_log(f"   -> Skipped (prefix mismatch)")
                        continue

                    # Status এবং OTP বের করা
                    status_text = re.sub(r'<[^>]+>', '', cols[1]).strip() if len(cols) > 1 else ""
                    otp = "N/A"
                    
                    # 🆕 আরও ভালো OTP pattern
                    otp_patterns = [
                        r'\b\d{4,6}\b',  # 4-6 digit OTP
                        r'OTP[:\s]*(\d+)',
                        r'Code[:\s]*(\d+)'
                    ]
                    for pattern in otp_patterns:
                        otp_match = re.search(pattern, status_text, re.IGNORECASE)
                        if otp_match:
                            otp = otp_match.group(1) if otp_match.lastindex else otp_match.group(0)
                            break

                    net_status = "PENDING"
                    if "SUCCESS" in status_text.upper() or otp != "N/A":
                        net_status = "SUCCESS"
                    elif any(x in status_text.upper() for x in ["CANCELED", "CANCELLED", "EXPIRED", "FAILED"]):
                        net_status = "FAILED"

                    bulk_data.append({"phone": phone, "otp": otp, "status": net_status})
                    add_log(f"✅ Valid number: {phone} | Status: {net_status} | OTP: {otp}")
                    break  # প্রথম ভ্যালিড নম্বর নিয়েই ব্রেক

                # 📤 ডাটাবেসে সেভ করা
                if bulk_data:
                    extracted_phone = bulk_data[0].get('phone')
                    
                    # 🟢 Duplicate Checker
                    if extracted_phone == bot_state.get("last_synced_phone"):
                        add_log(f"⚠️ Duplicate number detected: {extracted_phone} (waiting for new)")
                    else:
                        add_log(f"[*] Sending NEW number {extracted_phone} to Database...")
                        try:
                            db_res = requests.post(
                                f"{API_BRIDGE_URL}?action=save_bulk_numbers", 
                                json={"numbers": bulk_data}, 
                                timeout=15
                            )
                            add_log(f"[*] DB Response Status: {db_res.status_code}")
                            add_log(f"[*] DB Response Body: {db_res.text[:200]}")
                            
                            if db_res.status_code == 200:
                                try:
                                    resp_json = db_res.json()
                                    add_log(f"✅ DB Response: {resp_json}")
                                except:
                                    add_log(f"✅ DB Response (text): {db_res.text[:100]}")
                                bot_state["last_synced_phone"] = extracted_phone
                            else:
                                add_log(f"❌ DB Error: HTTP {db_res.status_code}", "ERROR")
                                
                            bot_state["status"] = f"🟢 Active | Last: {extracted_phone}"
                        except Exception as e:
                            add_log(f"❌ DB Connection Error: {e}", "ERROR")
                else:
                    if signal == "GET":
                        add_log("⚠️ No valid numbers found in table!")
                        # 🆕 ডিবাগ ইনফো
                        bot_state["debug_info"]["last_table_rows"] = len(all_rows)
                        bot_state["debug_info"]["last_page_url"] = driver.current_url
                
                time.sleep(10) 
                
        except Exception as e:
            add_log(f"❌ System Error: {e}", "ERROR")
            import traceback
            add_log(f"Traceback: {traceback.format_exc()[:300]}", "ERROR")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            time.sleep(5) 

bot_thread = threading.Thread(target=background_loop, daemon=True)
bot_thread.start()

@app.route('/')
def home():
    return jsonify(bot_state)

@app.route('/debug')
def debug():
    """🆕 ডিবাগ এন্ডপয়েন্ট"""
    return jsonify({
        "state": bot_state,
        "message": "Debug endpoint active"
    })

@app.route('/logs')
def logs():
    """🆕 শুধু লগ দেখার জন্য"""
    return jsonify({"logs": bot_state["action_logs"]})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    add_log(f"[*] Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
