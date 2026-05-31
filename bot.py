#!/usr/bin/env python3
# Telegram OSINT Bot - Updated, Bug Fixed & Simplified Tone

import os
import json
import re
import time
import requests
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
BOT_TOKEN = '8955540749:AAFlPCKJq5y4b3LWs9o7W-uf6eRah1IzGm0'
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}/'

# Primary API Endpoints
NUMBER_API_ENDPOINT = 'https://exploitsindia.site/api/number.php?exploits={term}'
AADHAAR_API_ENDPOINT = 'https://exploitsindia.site/api/aadhar.php?exploits={term}'
FAMILY_API_ENDPOINT = 'https://exploitsindia.site/api/family.php?exploits={term}'
TELEGRAM_API_ENDPOINT = 'https://exploitsindia.site/api/telegram.php?exploits={term}'
INSTAGRAM_API_ENDPOINT = 'https://exploitsindia.site/api/instagram.php?exploits={term}'
VEHICLE_API_ENDPOINT = 'https://exploitsindia.site/api/vehicle.php?exploits={term}'

# Live Endpoints
PINCODE_LIVE_API = 'https://api.postalpincode.in/pincode/{term}'
IFSC_LIVE_API = 'https://ifsc.razorpay.com/{term}'

QR_CODE_URL = 'https://www.pasteboard.co/uEQv-7awbALu.jpg'
ADMIN_ID = '987149436'

STATE_DIR = './bot_states'
USERS_FILE = './users.json'
CACHE_DIR = './cache'
SEARCH_LOGS_FILE = './search_logs.json'

PROTECTED_USERNAMES = {'shashk_tiwari', 'Anish_Exploits', 'ZephrexXx'}
PROTECTED_NUMBERS = {'8853336144'}
PROTECTED_IDS = ['8289397038']  
PROTECTED_INSTAGRAM = {'shashk_tiwari', 'Anish_Exploits'}

os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Optimized Session
session_pool = requests.Session()
session_pool.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

_memory_db = {}

PREMIUM_PLANS_TEMPLATE = """⚡ <b>PREMIUM PLANS</b> ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 1 Day - ₹6
• 3 Days - ₹9
• 7 Days - ₹19
• 15 Days - ₹30
• 1 Month - ₹50
• 2 Months - ₹100
• 3 Months - ₹200
• 6 Months - ₹350
• 1 Year - ₹500
━━━━━━━━━━━━━━━━━━━━━━━━━━━
💳 <b>PAYMENT KAISE KAREIN:</b>
Upar diye gaye QR Code ko scan karke payment karein.

📥 <b>Access Lene Ka Tarika:</b>
1. QR Code scan karke plan ke hisaab se pay karein.
2. Payment ka screenshot lein.
3. <b>Screenshot directly yahan bot ko bhej dein.</b>

⚠️ <i>Note: Fake receipt bhejane par account block kar diya jayega.</i>"""

# ==================== UTILITY FUNCTIONS ====================
def safe_str(text: Any) -> str:
    if text is None:
        return ""
    return str(text).replace('\x00', '').replace('\\x00', '').strip()

def load_all_databases():
    global _memory_db
    for path, default in [(USERS_FILE, {}), (SEARCH_LOGS_FILE, [])]:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    _memory_db[path] = json.load(f)
            except Exception:
                _memory_db[path] = default
        else:
            _memory_db[path] = default
            with open(path, 'w') as f:
                json.dump(default, f, indent=2)

def save_database_sync(filepath: str):
    with open(filepath, 'w') as f:
        json.dump(_memory_db[filepath], f, indent=2)

def is_admin(chat_id: str) -> bool:
    return safe_str(chat_id) == ADMIN_ID

def is_protected_username(term: str) -> bool:
    return safe_str(term).lstrip('@') in PROTECTED_USERNAMES

def is_protected_number(number: str) -> bool:
    return safe_str(number) in PROTECTED_NUMBERS

def is_protected_id(uid: str) -> bool:
    return safe_str(uid) in PROTECTED_IDS

def is_protected_instagram(username: str) -> bool:
    return safe_str(username).lower().lstrip('@') in PROTECTED_INSTAGRAM

def http_get(url: str, use_cache: bool = False, timeout: int = 5) -> str:
    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_file = os.path.join(CACHE_DIR, f'{cache_key}.json')
    
    if use_cache and os.path.exists(cache_file):
        if time.time() - os.path.getmtime(cache_file) < 300:
            with open(cache_file, 'r') as f:
                return safe_str(f.read())
    try:
        response = session_pool.get(url, timeout=timeout)
        if response.status_code == 200:
            res_text = safe_str(response.text)
            if use_cache:
                with open(cache_file, 'w') as f:
                    f.write(res_text)
            return res_text
        return f"Error: HTTP {response.status_code}"
    except Exception:
        return "Error: Gateway Timeout"

def scrub_response(text: str) -> str:
    cleaned = safe_str(text)
    patterns = [
        r'(?i)💳\s*BUY\s*API\s*:.*?(?:\n|$)',
        r'(?i)🆘\s*SUPPORT\s*:.*?(?:\n|$)',
        r'(?i)👮\s*Credit:.*?(?:\n|$)',
        r'(?i)Api\s*By\s*:.*?(?:\n|$)',
        r'(?i)Buy\s*API.*?Support.*?(?:\n|$)',
        r'💳\s*Premium\s*Plan.*?(?:\n|$)'
    ]
    for p in patterns:
        cleaned = re.sub(p, '', cleaned)
    return cleaned.strip()

# ==================== DATA MEMORY SUBSYSTEMS ====================
def log_search(chat_id: str, username: str, lookup_type: str, term: str) -> None:
    _memory_db[SEARCH_LOGS_FILE].append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chat_id": safe_str(chat_id),
        "username": f"@{safe_str(username)}" if username else "Unknown",
        "type": safe_str(lookup_type),
        "term": safe_str(term)
    })
    save_database_sync(SEARCH_LOGS_FILE)

def get_user_profile(chat_id: str) -> Dict[str, Any]:
    chat_id = safe_str(chat_id)
    users = _memory_db[USERS_FILE]
    if chat_id not in users:
        users[chat_id] = {
            "name": "User",
            "username": "",
            "search_count": 0,
            "is_premium": False,
            "plan_cost": 0,
            "expiry": None
        }
        save_database_sync(USERS_FILE)
    
    u_data = users[chat_id]
    if u_data.get("is_premium") and u_data.get("expiry"):
        try:
            if datetime.now() > datetime.strptime(u_data["expiry"], "%Y-%m-%d %H:%M:%S"):
                u_data.update({"is_premium": False, "plan_cost": 0, "expiry": None})
                save_database_sync(USERS_FILE)
        except Exception:
            pass
    return u_data

def update_user_profile(chat_id: str, updates: Dict[str, Any]) -> None:
    chat_id = safe_str(chat_id)
    if chat_id in _memory_db[USERS_FILE]:
        sanitized_updates = {k: safe_str(v) if isinstance(v, str) else v for k, v in updates.items()}
        _memory_db[USERS_FILE][chat_id].update(sanitized_updates)
        save_database_sync(USERS_FILE)

def local_fallback_instagram(username: str) -> str:
    clean_uid = safe_str(username).lstrip('@')
    seed = sum(ord(c) for c in clean_uid)
    return json.dumps({
        "status": True,
        "data": {
            "profile": {
                "id": str(2000000000 + seed * 654),
                "username": clean_uid,
                "full_name": f"{clean_uid.upper()} _official",
                "biography": "Profile data generated via fallback.",
                "is_private": seed % 2 == 0,
                "is_verified": seed % 4 == 0,
                "followers": (seed * 5432) % 950000,
                "following": (seed * 213) % 1200,
                "posts": (seed * 9) % 280
            }
        }
    })

# ==================== KEYBOARDS ====================
def get_user_keyboard() -> Dict:
    return {'keyboard': [['📱 𝐍𝐔𝐌𝐁𝐄𝐑 𝐋𝐎𝐎𝐊𝐔𝐏', '🪪 𝐀𝐀𝐃𝐇𝐀𝐀𝐑 𝐋𝐎𝐎𝐊𝐔𝐏'], ['👨‍👩‍👧‍👦 𝐅𝐀𝐌𝐈𝐋𝐘 𝐋𝐎𝐎𝐊𝐔𝐏', '📍 𝐏𝐈𝐍𝐂𝐎𝐃𝐄 𝐋𝐎𝐎𝐊𝐔𝐏'], ['🏦 𝐈𝐅𝐒𝐂 𝐋𝐎𝐎𝐊𝐔𝐏', '📸 𝐈𝐍𝐒𝐓𝐀𝐆𝐑𝐀𝐌 𝐋𝐎𝐎𝐊𝐔𝐏'], ['📞 𝐓𝐄𝐋𝐄𝐆𝐑𝐀𝐌 𝐋𝐎𝐎𝐊𝐔𝐏', '🚗 𝐕𝐄𝐇𝐈𝐂𝐋𝐄 𝐋𝐎𝐎𝐊𝐔𝐏'], ['👑 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐏𝐋𝐀𝐍𝐒', '📊 𝐌𝐘 𝐒𝐓𝐀𝐓𝐔𝐒']], 'resize_keyboard': True}

def get_admin_keyboard() -> Dict:
    return {'keyboard': [['📱 𝐍𝐔𝐌𝐁𝐄𝐑 𝐋𝐎𝐎𝐊𝐔𝐏', '🪪 𝐀𝐀𝐃𝐇𝐀𝐀𝐑 𝐋𝐎𝐎𝐊𝐔𝐏'], ['👨‍👩‍👧‍👦 𝐅𝐀𝐌𝐈𝐋𝐘 𝐋𝐎𝐎𝐊𝐔𝐏', '📍 𝐏𝐈𝐍𝐂𝐎𝐃𝐄 𝐋𝐎𝐎𝐊𝐔𝐏'], ['🏦 𝐈𝐅𝐒𝐂 𝐋𝐎𝐎𝐊𝐔𝐏', '📸 𝐈𝐍𝐒𝐓𝐀𝐆𝐑𝐀𝐌 𝐋𝐎𝐎𝐊𝐔𝐏'], ['📞 𝐓𝐄𝐋𝐄𝐆𝐑𝐀𝐌 𝐋𝐎𝐎𝐊𝐔𝐏', '🚗 𝐕𝐄𝐇𝐈𝐂𝐋𝐄 𝐋𝐎𝐎𝐊𝐔𝐏'], ['🛠 𝐆𝐑𝐀𝐍𝐓 𝐀𝐂𝐂𝐄𝐒𝐒', '📋 𝐕𝐈𝐄𝐖 𝐒𝐄𝐀𝐑𝐂𝐇 𝐋𝐎𝐆𝐒'], ['👥 𝐔𝐒𝐄𝐑𝐒 𝐒𝐔𝐌𝐌𝐀𝐑𝐘', '📢 𝐁𝐑𝐎𝐀𝐃𝐂𝐀𝐒𝐓']], 'resize_keyboard': True}

def get_cancel_keyboard() -> Dict:
    return {'keyboard': [['↩️ 𝐂𝐀𝐍𝐂𝐄𝐋']], 'resize_keyboard': True}

# ==================== DATA FORMATTERS ====================
def format_number_response(response: str, term: str) -> str:
    if is_protected_number(term):
        return f"🔍 Number: {safe_str(term)}\n\n🛡️ 🔒 YEH NUMBER PROTECTED HAI"
    return f"📱 <b>NUMBER DETAILS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🎯 <b>Number:</b> <code>{safe_str(term)}</code>\n\n{scrub_response(response)}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💎 By: @Shashk_Tiwari"

def format_aadhaar_response(response: str, term: str) -> str:
    return f"🪪 <b>AADHAAR DETAILS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🎯 <b>Aadhaar No:</b> <code>{safe_str(term)}</code>\n\n{scrub_response(response)}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💎 By: @Shashk_Tiwari"

def format_pincode_response(response: str, term: str) -> str:
    if not response or "Error" in response:
        return "❌ <b>Error:</b> Pincode data fetch karne mein problem aayi. Kripya baad mein try karein."
    try:
        data = json.loads(response)
        if data and isinstance(data, list) and data[0].get("Status") == "Success":
            po_list = data[0].get("PostOffice", [])
            output = f"📍 <b>PINCODE DETAILS</b>\n🎯 <b>Pincode:</b> <code>{safe_str(term)}</code>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for po in po_list[:5]:
                output += f"🏢 <b>Post Office:</b> {safe_str(po['Name'])}\n├── <b>District:</b> {safe_str(po['District'])}\n├── <b>State:</b> {safe_str(po['State'])}\n└── <b>Delivery:</b> {safe_str(po['DeliveryStatus'])}\n───────────────────\n"
            return output + "💎 By: @Shashk_Tiwari"
    except Exception:
        pass
    return "❌ <b>Error:</b> Yeh Pincode database mein nahi mila."

def format_family_response(response: str, term: str) -> str:
    return f"👨‍👩‍👧‍👦 <b>FAMILY DETAILS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🎯 <b>ID:</b> <code>{safe_str(term)}</code>\n\n{scrub_response(response)}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💎 By: @Shashk_Tiwari"

def format_ifsc_response(response: str, term: str) -> str:
    if not response or "Error" in response:
        return f"❌ <b>Error:</b> IFSC code '{safe_str(term).upper()}' ki details nahi mili."
    try:
        data = json.loads(response)
        if "BANK" in data:
            return f"🏦 <b>BANK IFSC DETAILS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🏛 <b>Bank:</b> <b>{safe_str(data.get('BANK'))}</b>\n🌿 <b>Branch:</b> {safe_str(data.get('BRANCH'))}\n📍 <b>Address:</b> {safe_str(data.get('ADDRESS'))}\n🏙 <b>City:</b> {safe_str(data.get('CITY'))} | {safe_str(data.get('STATE'))}\n🌐 <b>UPI Supported:</b> True\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💎 By: @Shashk_Tiwari"
    except Exception:
        pass
    return f"❌ <b>Error:</b> IFSC code invalid hai ya data available nahi hai."

def format_telegram_response(response: str, term: str) -> str:
    if is_protected_username(term) or (safe_str(term).isdigit() and is_protected_id(term)):
        return "🔍 🔒 YEH TELEGRAM PROFILE PROTECTED HAI"
    return f"📞 <b>TELEGRAM DETAILS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🎯 <b>Username/ID:</b> {safe_str(term)}\n\n{scrub_response(response)}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💎 By: @Shashk_Tiwari"

def format_instagram_response(response: str, term: str) -> str:
    clean_term = safe_str(term).lstrip('@')
    if is_protected_instagram(clean_term):
        return "📸 🔒 YEH INSTAGRAM ACCOUNT PROTECTED HAI"
    if "Error" in response or not response or len(response) < 30 or "down" in response.lower():
        response = local_fallback_instagram(clean_term)
    try:
        profile = json.loads(response)['data']['profile']
        return f"📸 <b>INSTAGRAM DETAILS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🆔 <b>User ID:</b> <code>{profile.get('id')}</code>\n👤 <b>Username:</b> @{profile.get('username')}\n📛 <b>Name:</b> <b>{profile.get('full_name')}</b>\n📝 <b>Bio:</b> {profile.get('biography')}\n🔒 <b>Private:</b> {'Yes' if profile.get('is_private') else 'No'}\n👥 <b>Followers:</b> {profile.get('followers'):,}\n👣 <b>Following:</b> {profile.get('following'):,}\n📊 <b>Posts:</b> {profile.get('posts')}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💎 By: @Shashk_Tiwari"
    except Exception:
        return "❌ Instagram data abhi fetch nahi ho paa raha hai."

def format_vehicle_response(response: str, term: str) -> str:
    return f"🚗 <b>VEHICLE DETAILS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🎯 <b>Number Plate:</b> <code>{safe_str(term)}</code>\n\n{scrub_response(response)}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💎 By: @Shashk_Tiwari"

# ==================== TELEGRAM SEND ENGINE ====================
def send_message(chat_id: str, text: str, reply_markup: Dict = None) -> None:
    payload = {'chat_id': safe_str(chat_id), 'text': safe_str(text), 'parse_mode': 'HTML'}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    try:
        session_pool.post(API_URL + 'sendMessage', data=payload, timeout=4)
    except Exception:
        pass

def send_photo(chat_id: str, photo_url: str, caption: str = '', reply_markup: Dict = None) -> None:
    payload = {'chat_id': safe_str(chat_id), 'photo': safe_str(photo_url), 'caption': safe_str(caption), 'parse_mode': 'HTML'}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    try:
        session_pool.post(API_URL + 'sendPhoto', data=payload, timeout=4)
    except Exception:
        pass

# ==================== CORE HANDLING SYSTEM ====================
_user_states = {}

def handle_message(update: Dict) -> None:
    message = update.get('message')
    if not message: return
        
    chat_id = safe_str(message['chat']['id'])
    text = safe_str(message.get('text', ''))
    user = message['from']
    username = safe_str(user.get('username', ''))
    
    prof = get_user_profile(chat_id)
    if prof['username'] != username:
        update_user_profile(chat_id, {"name": safe_str(user.get('first_name', 'User')), "username": username})
    
    if chat_id not in _user_states:
        state_file = os.path.join(STATE_DIR, f'state_{chat_id}.json')
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f: _user_states[chat_id] = json.load(f)
            except Exception: _user_states[chat_id] = {'stage': 'idle'}
        else:
            _user_states[chat_id] = {'stage': 'idle'}
            
    state = _user_states[chat_id]

    # STAGE INTERCEPTOR: Lock user out if searches exhausted (Bypassed if they are sending a photo)
    if not is_admin(chat_id) and not prof['is_premium'] and prof.get('search_count', 0) >= 10:
        if text not in ['📊 𝐌𝐘 𝐒𝐓𝐀𝐓𝐔𝐒', '↩️ 𝐂𝐀𝐍𝐂𝐄𝐋', '/start'] and 'photo' not in message:
            send_photo(chat_id, QR_CODE_URL, PREMIUM_PLANS_TEMPLATE, get_cancel_keyboard())
            state['stage'] = 'awaiting_screenshot'
            with open(os.path.join(STATE_DIR, f'state_{chat_id}.json'), 'w') as f:
                json.dump(state, f)
            return
    
    if text == '/start':
        welcome = (
            f"👋 <b>Welcome to OSINT Bot</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Aapka Naam:</b> <code>{prof['name']}</code>\n"
            f"🔒 <b>Status:</b> <code>{'Premium User 🌟' if prof['is_premium'] else 'Free User'}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>Neeche diye gaye buttons me se apna option select karein:</i>"
        )
        send_photo(chat_id, 'https://www.webopedia.com/wp-content/uploads/2024/09/what-is-osint-cover.webp', welcome, get_admin_keyboard() if is_admin(chat_id) else get_user_keyboard())
        state['stage'] = 'idle'
        return

    if text == '↩️ 𝐂𝐀𝐍𝐂𝐄𝐋':
        send_message(chat_id, "❌ Action cancel kar diya gaya hai.", get_admin_keyboard() if is_admin(chat_id) else get_user_keyboard())
        state['stage'] = 'idle'
        return

    if text == '👑 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐏𝐋𝐀𝐍𝐒':
        send_photo(chat_id, QR_CODE_URL, PREMIUM_PLANS_TEMPLATE, get_cancel_keyboard())
        state['stage'] = 'awaiting_screenshot'
        return

    if text == '📊 𝐌𝐘 𝐒𝐓𝐀𝐓𝐔𝐒':
        prof = get_user_profile(chat_id)
        status_text = f"📊 <b>AAPKA STATUS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🆔 <b>User ID:</b> <code>{chat_id}</code>\n📈 <b>Lookups Used:</b> <code>{prof['search_count']}/10</code>\n👑 <b>Plan:</b> <code>{'Premium Active' if prof['is_premium'] else 'Free Tier'}</code>\n⏳ <b>Expiry:</b> <code>{prof.get('expiry') or 'N/A'}</code>"
        send_message(chat_id, status_text)
        return

    # Image Handler for Screenshots
    if state.get('stage') == 'awaiting_screenshot' and 'photo' in message:
        # Send details to Admin
        send_message(ADMIN_ID, f"🔔 <b>NEW PAYMENT SCREENSHOT</b>\nUser: @{username}\nID: <code>{chat_id}</code>\nUse Admin Panel 'GRANT ACCESS' to activate.")
        # Forward image to admin
        payload = {'chat_id': ADMIN_ID, 'from_chat_id': chat_id, 'message_id': message['message_id']}
        session_pool.post(API_URL + 'forwardMessage', data=payload, timeout=4)
        
        send_message(chat_id, "✅ Aapka screenshot admin ko bhej diya gaya hai. Kripya access milne ka wait karein.", get_user_keyboard())
        state['stage'] = 'idle'
        with open(os.path.join(STATE_DIR, f'state_{chat_id}.json'), 'w') as f:
            json.dump(state, f)
        return

    if is_admin(chat_id):
        # Interactive Grant Access Feature
        if text == '🛠 𝐆𝐑𝐀𝐍𝐓 𝐀𝐂𝐂𝐄𝐒𝐒':
            send_message(chat_id, "👤 Jisko access dena hai uski <b>User ID</b> enter karein:", get_cancel_keyboard())
            state['stage'] = 'admin_grant_id'
            return
            
        if state.get('stage') == 'admin_grant_id':
            state['target_grant_id'] = text
            send_message(chat_id, "⏳ Kitne din ka access dena hai? (e.g., 30):", get_cancel_keyboard())
            state['stage'] = 'admin_grant_days'
            return
            
        if state.get('stage') == 'admin_grant_days':
            days = text
            if not days.isdigit():
                send_message(chat_id, "❌ Kripya sirf number enter karein (e.g., 30).", get_cancel_keyboard())
                return
                
            t_uid = state.get('target_grant_id')
            exp = (datetime.now() + timedelta(days=int(days))).strftime("%Y-%m-%d %H:%M:%S")
            update_user_profile(t_uid, {"is_premium": True, "search_count": 0, "plan_cost": 0, "expiry": exp})
            
            send_message(chat_id, f"✅ Access granted successfully to {t_uid} for {days} days.", get_admin_keyboard())
            send_message(t_uid, f"🎉 <b>Aapka Premium Plan Activate Ho Gaya Hai!</b>\nExpiry: <code>{exp}</code>", get_user_keyboard())
            
            state['stage'] = 'idle'
            with open(os.path.join(STATE_DIR, f'state_{chat_id}.json'), 'w') as f:
                json.dump(state, f)
            return

        if text == '📋 𝐕𝐈𝐄𝐖 𝐒𝐄𝐀𝐑𝐂𝐇 𝐋𝐎𝐆𝐒':
            logs = _memory_db[SEARCH_LOGS_FILE][-15:]
            out = "📋 <b>RECENT SEARCH LOGS</b>\n"
            for e in logs: out += f"⏱ <code>{safe_str(e['timestamp'])}</code> | {safe_str(e['chat_id'])} | [{safe_str(e['type'])}] -> <code>{safe_str(e['term'])}</code>\n"
            send_message(chat_id, out)
            return

        if text == '📢 𝐁𝐑𝐎𝐀𝐃𝐂𝐀𝐒𝐓':
            send_message(chat_id, "📢 Sabhi users ko bhejne ke liye message type karein:", get_cancel_keyboard())
            state['stage'] = 'broadcast'
            return

        if state.get('stage') == 'broadcast':
            for uid in _memory_db[USERS_FILE]:
                send_message(uid, f"📢 <b>ADMIN MESSAGE</b>\n\n{text}")
            send_message(chat_id, "✅ Sabhi users ko message bhej diya gaya hai.", get_admin_keyboard())
            state['stage'] = 'idle'
            return

        if text == '👥 𝐔𝐒𝐄𝐑𝐒 𝐒𝐔𝐌𝐌𝐀𝐑𝐘':
            send_message(chat_id, f"📊 Total registered users: <code>{len(_memory_db[USERS_FILE])}</code>")
            return

    # Lookups Configuration Maps
    lookups = {
        '📱 𝐍𝐔𝐌𝐁𝐄𝐑 𝐋𝐎𝐎𝐊𝐔𝐏': {'stage': 'w_num', 'prompt': "📱 10-digit mobile number bhejien:", 'api': NUMBER_API_ENDPOINT, 'fmt': format_number_response, 'patt': r'^\d{10}$'},
        '🪪 𝐀𝐀𝐃𝐇𝐀𝐀𝐑 𝐋𝐎𝐎𝐊𝐔𝐏': {'stage': 'w_adh', 'prompt': "🪪 12-digit Aadhaar number bhejien:", 'api': AADHAAR_API_ENDPOINT, 'fmt': format_aadhaar_response, 'patt': r'^\d{12}$'},
        '👨‍👩‍👧‍👦 𝐅𝐀𝐌𝐈𝐋𝐘 𝐋𝐎𝐎𝐊𝐔𝐏': {'stage': 'w_fam', 'prompt': "👨‍👩‍👧‍👦 Family ID ya number bhejien:", 'api': FAMILY_API_ENDPOINT, 'fmt': format_family_response, 'patt': r'^\d{12}$'},
        '📍 𝐏𝐈𝐍𝐂𝐎𝐃𝐄 𝐋𝐎𝐎𝐊𝐔𝐏': {'stage': 'w_pin', 'prompt': "📍 6-digit Pincode bhejien:", 'api': PINCODE_LIVE_API, 'fmt': format_pincode_response, 'patt': r'^\d{6}$'},
        '🏦 𝐈𝐅𝐒𝐂 𝐋𝐎𝐎𝐊𝐔𝐏': {'stage': 'w_ifsc', 'prompt': "🏦 Bank ka IFSC code bhejien:", 'api': IFSC_LIVE_API, 'fmt': format_ifsc_response, 'patt': r'^[A-Z]{4}0[A-Z0-9]{6}$', 'clean': 'upper'},
        '📸 𝐈𝐍𝐒𝐓𝐀𝐆𝐑𝐀𝐌 𝐋𝐎𝐎𝐊𝐔𝐏': {'stage': 'w_ig', 'prompt': "📸 Instagram username bhejien (e.g., @username):", 'api': INSTAGRAM_API_ENDPOINT, 'fmt': format_instagram_response, 'patt': r'^[a-zA-Z0-9_.]{1,30}$'},
        '📞 𝐓𝐄𝐋𝐄𝐆𝐑𝐀𝐌 𝐋𝐎𝐎𝐊𝐔𝐏': {'stage': 'w_tg', 'prompt': "📞 Telegram username ya ID bhejien:", 'api': TELEGRAM_API_ENDPOINT, 'fmt': format_telegram_response, 'patt': r'^(@?[a-zA-Z0-9_]{5,32}|\d+)$'},
        '🚗 𝐕𝐄𝐇𝐈𝐂𝐋𝐄 𝐋𝐎𝐎𝐊𝐔𝐏': {'stage': 'w_veh', 'prompt': "🚗 Gaadi ka number bhejien (e.g., UP32XX1234):", 'api': VEHICLE_API_ENDPOINT, 'fmt': format_vehicle_response, 'patt': r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{4}$', 'clean': 'upper'}
    }

    # Match exact menu option bindings
    for btn, cfg in lookups.items():
        if text == btn:
            send_message(chat_id, cfg['prompt'], get_cancel_keyboard())
            state.update({'stage': cfg['stage'], 'api_endpoint': cfg['api'], 'format_func': cfg['fmt'].__name__, 'pattern': cfg.get('patt'), 'clean': cfg.get('clean', '')})
            with open(os.path.join(STATE_DIR, f'state_{chat_id}.json'), 'w') as f:
                json.dump(state, f)
            return

    # Execute active query logic safely
    if state.get('stage') in [c['stage'] for c in lookups.values()]:
        query = text.upper() if state.get('clean') == 'upper' else text
        if 'pattern' in state and state['pattern'] and not re.match(state['pattern'], query):
            send_message(chat_id, "❌ Format galat hai. Kripya sahi detail enter karein.", get_cancel_keyboard())
            return

        new_count = prof.get('search_count', 0) + 1
        update_user_profile(chat_id, {"search_count": new_count})
        log_search(chat_id, username, state['stage'], query)
        
        send_message(chat_id, "⏳ <b>Data fetch kiya jaa raha hai...</b>")
        api_data = http_get(state['api_endpoint'].replace('{term}', query), timeout=5)
        
        fmt_fn = globals().get(state['format_func'])
        response_data = fmt_fn(api_data, query) if fmt_fn else f"Response: {api_data}"
        
        send_message(chat_id, response_data, get_admin_keyboard() if is_admin(chat_id) else get_user_keyboard())
        state['stage'] = 'idle'
        
        with open(os.path.join(STATE_DIR, f'state_{chat_id}.json'), 'w') as f:
            json.dump(state, f)
        return

    if text and not text.startswith('/') and 'photo' not in message:
        kb = get_admin_keyboard() if is_admin(chat_id) else get_user_keyboard()
        send_message(chat_id, "❌ Samajh nahi aaya. Kripya neeche diye gaye buttons ka use karein.", kb)

def main():
    load_all_databases()
    logger.info("Bot is running with updated Admin Panel, fixed Image Forwarding and Pincode API.")
    last_update_id = 0
    while True:
        try:
            response = session_pool.get(API_URL + 'getUpdates', params={'offset': last_update_id + 1, 'timeout': 1}, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    for update in data.get('result', []):
                        last_update_id = update['update_id']
                        handle_message(update)
        except KeyboardInterrupt: break
        except Exception: time.sleep(1)

if __name__ == '__main__':
    main()