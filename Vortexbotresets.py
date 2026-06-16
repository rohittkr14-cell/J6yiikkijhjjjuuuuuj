#!/usr/bin/env python3
# =============================================================================
# VORTEX BOT v5.0 - WITH SUBSCRIPTION SYSTEM
# Instagram Password Reset + Account Recovery via Telegram
# By @xtxz7 | @kai_olds | @louis_olds
# =============================================================================

import os, sys, time, random, string, json, uuid, re, asyncio, threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# ─── AUTO INSTALL ──────────────────────────────────────────────────────────
try:
    import requests
    from telethon import TelegramClient, events, Button, utils
    from telethon.sessions import StringSession
except ImportError:
    os.system("pip install requests telethon --upgrade -q")
    import requests
    from telethon import TelegramClient, events, Button, utils
    from telethon.sessions import StringSession

try:
    import httpx
except ImportError:
    os.system("pip install httpx[http2] -q")
    import httpx

# ═══════════════════════════════════════════════════════════════════════════
# PART 1 - CONFIG + INSTAGRAM ENGINES
# ═══════════════════════════════════════════════════════════════════════════

API_ID = 35964213
API_HASH = "49f6f929d59ba8c565c498015a48adb1"
BOT_TOKEN = "8329637980:AAEYTmDHvd2tae1NRNTOhz8vkuRuARUdhhM"
ADMIN_IDS = [7691071175]
CONFIG_FILE = "channelsss_config.json"
USERS_FILE = "userszszz.json"
SUBSCRIPTIONS_FILE = "subscriptions.json"
PENDING_PAYMENTS_FILE = "pending_payments.json"

# ─── DEFAULT CHANNELS ────────────────────────────────────────────────────
CHANNELS = {
    1: {
        "type": "public",
        "link": "https://t.me/vrtxportal",
        "username": "@vrtxportal",
        "invite_link": "https://t.me/vrtxportal"
    }
}

# ─── SUBSCRIPTION PLANS ──────────────────────────────────────────────────
SUBSCRIPTION_PLANS = {
    "1day":   {"label": "1 Day",       "duration_days": 1,   "price": 35,  "price_display": "₹35"},
    "7days":  {"label": "7 Days",      "duration_days": 7,   "price": 199, "price_display": "₹199"},
    "1month": {"label": "1 Month",     "duration_days": 30,  "price": 799, "price_display": "₹799"},
    "permanent": {"label": "Permanent", "duration_days": None, "price": 1599, "price_display": "₹1599"},
}

# ─── UPI CONFIG (EDIT THIS) ──────────────────────────────────────────────
UPI_ID = "Zioxrohit@fam"  # ← CHANGE THIS
UPI_NAME = "Rohit Kumar"
QR_FILE = "qrfpf.jpg"  # QR code image file path

user_state = {}
user_tokens = {}
user_chat_ids = {}
executor = ThreadPoolExecutor(max_workers=20)

# ─── USERS (File-based) ───────────────────────────────────────────────────
registered_users = {}
subscriptions = {}        # {user_id: {"plan": str, "expires_at": str or None(Permanent), "active": bool}}
pending_payments = {}     # {payment_id: {"user_id": int, "plan": str, "txn_id": str, "screenshot_file_id": str, "status": "pending", "timestamp": str}}
last_update_id = 0

P = '\033[35m'; G = '\033[92m'; Y = '\033[1;33m'; Z = '\033[1;31m'
B = '\033[94m'; N = '\033[1;37m'; J = '\033[2;36m'; E = '\033[38;5;208m'

def load_channels():
    global CHANNELS
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                for k, v in json.load(f).items():
                    if "type" not in v: v["type"]="public"; v["invite_link"]=v.get("link","")
                    CHANNELS[int(k)] = v
        except: pass
    save_channels()

def save_channels():
    with open(CONFIG_FILE,"w") as f: json.dump({str(k):v for k,v in CHANNELS.items()},f,indent=2)

def load_users():
    global registered_users
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                data = json.load(f)
                for k, v in data.items():
                    registered_users[int(k)] = v
        except: pass

def save_users():
    with open(USERS_FILE,"w") as f:
        json.dump({str(k):v for k,v in registered_users.items()}, f, indent=2)

def load_subscriptions():
    global subscriptions
    if os.path.exists(SUBSCRIPTIONS_FILE):
        try:
            with open(SUBSCRIPTIONS_FILE) as f:
                data = json.load(f)
                subscriptions = {int(k): v for k, v in data.items()}
        except: pass

def save_subscriptions():
    with open(SUBSCRIPTIONS_FILE, "w") as f:
        json.dump({str(k): v for k, v in subscriptions.items()}, f, indent=2)

def load_pending_payments():
    global pending_payments
    if os.path.exists(PENDING_PAYMENTS_FILE):
        try:
            with open(PENDING_PAYMENTS_FILE) as f:
                data = json.load(f)
                pending_payments = {k: v for k, v in data.items()}
        except: pass

def save_pending_payments():
    with open(PENDING_PAYMENTS_FILE, "w") as f:
        json.dump(pending_payments, f, indent=2)

load_users()
load_subscriptions()
load_pending_payments()

def register_user(uid, username=None, first_name=None):
    global registered_users
    if uid not in registered_users:
        registered_users[uid] = {
            "username": username or "",
            "first_name": first_name or "",
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_users()
        print(f"{G}[+] User registered: {uid}{N}")

load_channels()

# ─── SUBSCRIPTION HELPERS ─────────────────────────────────────────────────

def check_subscription(uid):
    """Returns (has_access: bool, plan_info: str or None)"""
    if uid in ADMIN_IDS:
        return True, "Admin (unlimited)"
    
    sub = subscriptions.get(uid)
    if not sub or not sub.get("active"):
        return False, None
    
    plan = sub.get("plan", "")
    expires_at = sub.get("expires_at")
    
    # Permanent access
    if plan == "permanent":
        return True, "Permanent Access"
    
    # Check expiry
    if expires_at:
        try:
            expiry = datetime.fromisoformat(expires_at)
            if datetime.now() > expiry:
                sub["active"] = False
                save_subscriptions()
                return False, f"Expired on {expiry.strftime('%Y-%m-%d %H:%M')}"
            days_left = (expiry - datetime.now()).days
            hours_left = int((expiry - datetime.now()).total_seconds() / 3600)
            if days_left > 0:
                return True, f"{plan} - {days_left}d remaining"
            else:
                return True, f"{plan} - {hours_left}h remaining"
        except:
            pass
    
    return False, None

def activate_subscription(uid, plan_key):
    """Activate or extend a subscription for a user."""
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        return False
    
    now = datetime.now()
    
    if uid not in subscriptions:
        subscriptions[uid] = {"active": False, "plan": "", "expires_at": None}
    
    sub = subscriptions[uid]
    
    if plan_key == "permanent":
        sub["plan"] = "permanent"
        sub["expires_at"] = None
        sub["active"] = True
    else:
        days = plan["duration_days"]
        if sub.get("active") and sub.get("expires_at") and sub.get("plan") == plan_key:
            # Extend existing subscription
            try:
                current_expiry = datetime.fromisoformat(sub["expires_at"])
                if current_expiry > now:
                    new_expiry = current_expiry + timedelta(days=days)
                else:
                    new_expiry = now + timedelta(days=days)
            except:
                new_expiry = now + timedelta(days=days)
        else:
            new_expiry = now + timedelta(days=days)
        
        sub["plan"] = plan_key
        sub["expires_at"] = new_expiry.isoformat()
        sub["active"] = True
    
    save_subscriptions()
    return True

# ─── CHANNEL CHECK ─────────────────────────────────────────────────────────
def check_user_channels_sync(user_id):
    not_joined = []
    for idx, ch_data in CHANNELS.items():
        username = ch_data.get("username","").lstrip("@")
        if not username:
            not_joined.append(idx)
            continue
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember",params={"chat_id":f"@{username}","user_id":user_id},timeout=4)
            data = r.json()
            if data.get("ok"):
                status = data["result"]["status"]
                if status in ("member","administrator","creator","restricted"):
                    continue
            not_joined.append(idx)
        except:
            not_joined.append(idx)
    return len(not_joined)==0, not_joined

async def check_user_channels(user_id):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, check_user_channels_sync, user_id)

# ═══════════════════════════════════════════════════════════════════════════
# ENGINE 1 - PASSWORD RESET VIA LINK (Original)
# ═══════════════════════════════════════════════════════════════════════════

def gen_dev(cp):
    aid = f"android-{''.join(random.choices(string.hexdigits.lower(),k=16))}"
    ua = f"Instagram 394.0.0.46.81 Android ({random.choice(['28/9','29/10','30/11','31/12'])}; {random.choice(['240dpi','320dpi','480dpi'])}; {random.choice(['720x1280','1080x1920','1440x2560'])}; {random.choice(['samsung','xiaomi','huawei','oneplus','google'])}; {random.choice(['SM-G975F','Mi-9T','P30-Pro','ONEPLUS-A6003','Pixel-4'])}; intel; en_US; {random.randint(100000000,999999999)})"
    wid = str(uuid.uuid4())
    pw = f'#PWD_INSTAGRAM:0:{int(datetime.now().timestamp())}:{cp}'
    return aid, ua, wid, pw

def mkh(mid="", ua=""):
    return {"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8","X-Bloks-Version-Id":"e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd","X-Mid":mid,"User-Agent":ua,"Content-Length":"9481"}

def id_user(uid):
    try:
        r = requests.get(f"https://i.instagram.com/api/v1/users/{uid}/info/",headers={"User-Agent":"Instagram 219.0.0.12.117 Android","Accept":"application/json","X-IG-App-ID":"936619743392459"},timeout=5)
        if "<!DOCTYPE" in r.text: return "Private/Deleted"
        return r.json()["user"]["username"]
    except: return "Unknown"

def reset_pass(link, pw):
    try:
        aid, ua, wid, PASSWORD = gen_dev(pw)
        uidb36 = link.split("uidb36=")[1].split("&token=")[0]
        token = link.split("&token=")[1].split(":")[0]
        r = requests.post("https://i.instagram.com/api/v1/accounts/password_reset/",headers=mkh(ua=ua),data={"source":"one_click_login_email","uidb36":uidb36,"device_id":aid,"token":token,"waterfall_id":wid},timeout=15)
        if "user_id" not in r.text:
            if "challenge_required" in r.text: return {"success":False,"error":"Account has 2FA/security challenge."}
            if "expired" in r.text.lower(): return {"success":False,"error":"Reset link expired."}
            return {"success":False,"error":"Invalid reset link"}
        mid = r.headers.get("Ig-Set-X-Mid","")
        j = r.json()
        uid, cni = j["user_id"], j["cni"]
        nn = j.get("nonce_code","")
        cc = j.get("challenge_context","")
        u2 = "https://i.instagram.com/api/v1/bloks/apps/com.instagram.challenge.navigation.take_challenge/"
        d2 = {"user_id":str(uid),"cni":str(cni),"nonce_code":str(nn),"bk_client_context":'{"bloks_version":"e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd","styles_id":"instagram"}',"challenge_context":str(cc),"bloks_versioning_id":"e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd","get_challenge":"true"}
        r2 = requests.post(u2,headers=mkh(mid,ua),data=d2,timeout=15).text.replace('\\','')
        try: ccf = r2.split(f'(bk.action.i64.Const, {cni}), "')[1].split('", (bk.action.bool.Const, false)))')[0]
        except: return {"success":False,"error":"Challenge extraction failed"}
        d3 = {"is_caa":"False","source":"","uidb36":uidb36,"error_state":json.dumps({"type_name":"str","index":0,"state_id":1048583541}),"afv":"","cni":str(cni),"token":token,"has_follow_up_screens":"0","bk_client_context":json.dumps({"bloks_version":"e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd","styles_id":"instagram"}),"challenge_context":ccf,"bloks_versioning_id":"e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd","enc_new_password1":PASSWORD,"enc_new_password2":PASSWORD}
        requests.post(u2,headers=mkh(mid,ua),data=d3,timeout=15)
        uname = id_user(uid)
        return {"success":True,"password":pw,"user_id":uid,"username":uname}
    except Exception as e:
        return {"success":False,"error":f"Connection error or rate limited: {str(e)}"}

# ═══════════════════════════════════════════════════════════════════════════
# ENGINE 2 - ACCOUNT RECOVERY (Send Email/SMS via account_recovery_send_ajax)
# ═══════════════════════════════════════════════════════════════════════════

def account_recovery(email_or_username):
    try:
        url = "https://www.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/"
        headers = {"User-Agent":"Instagram Android","x-csrftoken":"missing","accept-language":"tr-TR,tr;q=0.9","content-type":"application/x-www-form-urlencoded; charset=UTF-8","x-requested-with":"XMLHttpRequest","referer":"https://www.instagram.com/accounts/password/reset/"}
        data = {"email_or_username": email_or_username, "flow": "fxcal"}
        with httpx.Client(http2=True, headers=headers) as c:
            r = c.post(url, data=data)
            if r.status_code == 200:
                try:
                    resp = r.json()
                    if resp.get("status")=="ok" or resp.get("status")=="success":
                        return {"success":True,"response":resp,"message":f"✅ Recovery email/SMS sent to {email_or_username}"}
                    elif "sent" in str(resp).lower():
                        return {"success":True,"response":resp,"message":f"✅ Recovery sent to {email_or_username}"}
                    else:
                        return {"success":True,"response":resp,"message":f"✅ Response: {json.dumps(resp, indent=2)}"}
                except:
                    return {"success":True,"response":r.text[:200],"message":f"✅ Request sent to {email_or_username}"}
            else:
                return {"success":False,"error":f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"success":False,"error":f"Connection error: {str(e)}"}

# ═══════════════════════════════════════════════════════════════════════════
# PART 2 - UI: /start MENU WITH SUBSCRIPTION PANEL
# ═══════════════════════════════════════════════════════════════════════════

client = TelegramClient(StringSession(), API_ID, API_HASH).start(bot_token=BOT_TOKEN)
print(f"{G}[+] VORTEX v5.0 - WITH SUBSCRIPTION SYSTEM{N}")
print(f"{G}[+] Mode: GROUP + DM - ALAG HANDLERS{N}")

def mk_btns(nj):
    btns = []
    for idx in nj:
        cd = CHANNELS.get(idx,{})
        lbl = "🔒" if cd.get("type")=="private" else "📢"
        link = cd.get("invite_link") or cd.get("link","")
        btns.append([Button.url(f"{lbl} Channel {idx}", link)])
    if btns: btns.append([Button.inline("✅ Joined All", b"joined")])
    return btns

def make_subscription_buttons():
    """Main subscription panel with 4 plan buttons."""
    return [
        [Button.inline("🌟 1 DAY  -  ₹35", b"sub_1day")],
        [Button.inline("🔥 7 DAYS - ₹199", b"sub_7days")],
        [Button.inline("⚡ 1 MONTH - ₹799", b"sub_1month")],
        [Button.inline("💎 PERMANENT - ₹1599", b"sub_permanent")],
        [Button.inline("🔙 Back to Menu", b"back_menu")]
    ]

def make_plan_buttons():
    """After channel verification, show subscription options."""
    return [
        [Button.inline("🔐 RESET VIA LINK", b"mode_link")],
        [Button.inline("📧 LINK SENT (Email)", b"mode_recovery")],
        [Button.inline("💳 SUBSCRIPTION PLANS", b"show_subscription")]
    ]

# ═══════════════════════════════════════════════════════════════════════════
# TELEGRAM CLIENT EVENTS (DM ke liye)
# ═══════════════════════════════════════════════════════════════════════════

# ─── CALLBACK HANDLER (for all inline buttons) ─────────────────────────────
@client.on(events.CallbackQuery)
async def callback_handler(event):
    s = await event.get_sender()
    uid = s.id
    data = event.data
    
    # ── Channel join verification ──
    if data == b"joined":
        all_joined, nj = await check_user_channels(uid)
        if all_joined:
            user_state[uid] = {"step": "main_menu", "mode": "link"}
            # Show main menu after verification
            msg = (
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**⚡ VORTEX PREMIUM v5.0**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "👋 **Welcome to VORTEX Premium!**\n\n"
                "🔐 **Instagram Account Recovery Tool**\n\n"
                "➡️ **Choose a mode below** to get started\n"
                "💳 **Subscribe** for unlimited access\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**⚡ By @dochains**"
            )
            await event.edit(msg, buttons=make_plan_buttons())
        else:
            msg = "❌ **NOT VERIFIED**\n\n"
            for idx in nj:
                cd = CHANNELS.get(idx,{})
                msg += f"❌ **Channel {idx}:** {cd.get('username','')}\n"
            msg += "\nJoin and tap button again"
            await event.edit(msg, buttons=mk_btns(nj))
        return
    
    # ── Show Subscription Panel ──
    if data == b"show_subscription":
        has_access, plan_info = check_subscription(uid)
        sub_status = f"✅ **Active:** {plan_info}" if has_access else "❌ **No Active Subscription**"
        msg = (
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**💳 SUBSCRIPTION PLANS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{sub_status}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**📌 Choose your plan:**\n\n"
            "🌟 **1 DAY**    - **₹35**\n"
            "🔥 **7 DAYS**   - **₹199**\n"
            "⚡ **1 MONTH**  - **₹799**\n"
            "💎 **PERMANENT** - **₹1599**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💳 **UPI:** `{}`\n".format(UPI_ID) +
            "━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await event.edit(msg, buttons=make_subscription_buttons())
        return
    
    # ── Handle Plan Selection → Payment Info ──
    if data.startswith(b"sub_"):
        plan_key = data.decode().split("_")[1]  # 1day, 7days, 1month, permanent
        plan = SUBSCRIPTION_PLANS.get(plan_key)
        if not plan:
            return await event.answer("Invalid plan selected!")
        
        # Store the selected plan in user state
        user_state[uid] = {"step": "awaiting_payment", "mode": "link", "selected_plan": plan_key}
        
        msg = (
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**💳 PAYMENT - {plan['label']}**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Plan:** {plan['label']}\n"
            f"**Amount:** {plan['price_display']}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**📱 PAY USING UPI:**\n\n"
            f"**UPI ID:** `{UPI_ID}`\n"
            f"**Name:** {UPI_NAME}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**📋 STEPS:**\n"
            "1️⃣ Scan QR or pay to UPI ID above\n"
            "2️⃣ Send the **Transaction ID (UTR)**\n"
            "3️⃣ Send the **Payment Screenshot**\n"
            "4️⃣ Tap **✅ I HAVE PAID**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        btns = [
            [Button.inline("✅ I HAVE PAID", b"paid_confirm")],
            [Button.inline("🔙 Back to Plans", b"show_subscription")]
        ]
        
        await event.edit(msg, buttons=btns)
        return
    
    # ── User says they have paid ──
    if data == b"paid_confirm":
        st = user_state.get(uid, {})
        if st.get("step") != "awaiting_payment":
            return await event.answer("Please select a plan first!")
        
        user_state[uid] = {"step": "awaiting_txn_id", "mode": "link", "selected_plan": st.get("selected_plan")}
        
        msg = (
            "✅ **Great! Please send your Transaction ID (UTR Number)**\n\n"
            "📝 Example: `HDFC123456789`\n\n"
            "Send it as a text message below:"
        )
        await event.edit(msg, buttons=[[Button.inline("🔙 Cancel", b"show_subscription")]])
        return
    
    # ── Handle mode_link and mode_recovery (access check) ──
    if data == b"mode_link":
        has_access, plan_info = check_subscription(uid)
        if not has_access and uid not in ADMIN_IDS:
            return await event.answer("❌ No active subscription! Subscribe first.", alert=True)
        
        user_state[uid] = {"step":"link","mode":"link"}
        await event.edit(
            "**🔐 RESET VIA LINK MODE**\n\n"
            "📌 **STEPS:**\n"
            "1️⃣ Send Instagram **Reset Link** (with uidb36=)\n"
            "2️⃣ Send **New Password**\n"
            "3️⃣ Done ✅\n\n"
            "**📤 Send reset link:**",
            buttons=[[Button.inline("🔙 Back to Menu", b"back_menu")]]
        )
        return
    
    if data == b"mode_recovery":
        has_access, plan_info = check_subscription(uid)
        if not has_access and uid not in ADMIN_IDS:
            return await event.answer("❌ No active subscription! Subscribe first.", alert=True)
        
        user_state[uid] = {"step":"recovery_username","mode":"recovery"}
        await event.edit(
            "**📧 ACCOUNT RECOVERY MODE**\n\n"
            "Send Instagram **Username or Email**\n"
            "to trigger password reset email/SMS.\n\n"
            "**📤 Send username or email:**",
            buttons=[[Button.inline("🔙 Back to Menu", b"back_menu")]]
        )
        return
    
    if data == b"back_menu":
        user_state[uid] = {"step": "main_menu", "mode": "link"}
        msg = (
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**⚡ VORTEX PREMIUM v5.0**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "👋 **Welcome to VORTEX Premium!**\n\n"
            "🔐 **Instagram Account Recovery Tool**\n\n"
            "➡️ **Choose a mode below** to get started\n"
            "💳 **Subscribe** for unlimited access\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**⚡ By @dochains**"
        )
        await event.edit(msg, buttons=make_plan_buttons())
        return

# ─── /START ────────────────────────────────────────────────────────────────
@client.on(events.NewMessage(pattern="/start"))
async def start_cmd(event):
    s = await event.get_sender()
    uid = s.id
    if event.is_group or event.is_channel: return
    register_user(uid, s.username, s.first_name)
    print(f"{G}[Telethon][DM] /start from {uid}{N}")
    
    all_joined, nj = await check_user_channels(uid)
    if all_joined:
        user_state[uid] = {"step": "main_menu", "mode": "link"}
        msg = (
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**⚡ VORTEX PREMIUM v5.0**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "👋 **Welcome to VORTEX Premium!**\n\n"
            "🔐 **Instagram Account Recovery Tool**\n\n"
            "➡️ **Choose a mode below** to get started\n"
            "💳 **Subscribe** for unlimited access\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**⚡ By @dochains**"
        )
        await event.respond(msg, buttons=make_plan_buttons())
    else:
        msg = "⚠️ **VERIFICATION REQUIRED**\n\n"
        for idx in nj:
            cd = CHANNELS.get(idx,{})
            typ = cd.get("type","public")
            if typ == "private":
                msg += f"🔒 **Channel {idx}:** {cd.get('username','')} (Request to Join)\n"
            else:
                msg += f"❌ **Channel {idx}:** {cd.get('username','')}\n"
        if any(CHANNELS.get(i,{}).get("type")=="private" for i in nj):
            msg += "\n🔒 **Private Channel:** Click link → Tap 'Request to Join' → Wait for approval"
        msg += "\n\nThen tap **✅ Joined All**"
        await event.respond(msg, buttons=mk_btns(nj))

# ═══════════════════════════════════════════════════════════════════════════
# PART 3 - DM MESSAGE HANDLER (Telethon - Private Messages)
# ═══════════════════════════════════════════════════════════════════════════

@client.on(events.NewMessage)
async def dm_msg_handler(event):
    """Sirf DM messages"""
    if not event.is_private:
        return
    
    s = await event.get_sender()
    uid = s.id
    
    if event.message.text and event.message.text.startswith("/"):
        return
    
    txt = event.message.text.strip()
    if not txt:
        return
    
    print(f"{G}[Telethon][DM] MSG from {uid}: {txt[:50]}{N}")
    register_user(uid, s.username, s.first_name)
    
    all_joined, nj = await check_user_channels(uid)
    if not all_joined:
        msg = "⚠️ **VERIFICATION REQUIRED**\n\n"
        for idx in nj:
            cd = CHANNELS.get(idx,{})
            typ = cd.get("type","public")
            if typ == "private":
                msg += f"🔒 **Channel {idx}:** {cd.get('username','')} (Request to Join)\n"
            else:
                msg += f"❌ **Channel {idx}:** {cd.get('username','')}\n"
        msg += "\nTap **✅ Joined All** when done"
        return await event.respond(msg, buttons=mk_btns(nj))
    
    if uid not in user_state:
        user_state[uid] = {"step": "main_menu", "mode": "link"}
    
    st = user_state[uid]
    
    # ── If user is in payment flow (awaiting transaction ID) ──
    if st.get("step") == "awaiting_txn_id":
        # Save the transaction ID
        user_state[uid] = {
            "step": "awaiting_screenshot",
            "mode": "link",
            "selected_plan": st.get("selected_plan"),
            "txn_id": txt
        }
        await event.respond(
            "✅ **Transaction ID Saved!**\n\n"
            "📸 **Now send the payment screenshot/QR payment confirmation image.**\n\n"
            "Send it as a **photo/image** below:",
            buttons=[[Button.inline("🔙 Cancel", b"show_subscription")]]
        )
        return
    
    # ── Check access for tool usage ──
    if st.get("step") not in ("awaiting_txn_id", "awaiting_screenshot", "main_menu"):
        has_access, plan_info = check_subscription(uid)
        if not has_access and uid not in ADMIN_IDS:
            # Check if they've at least started payment flow
            await event.respond(
                "❌ **No Active Subscription!**\n\n"
                "Please subscribe first to use VORTEX tools.\n"
                "💳 Tap below to see plans:",
                buttons=[[Button.inline("💳 SUBSCRIPTION PLANS", b"show_subscription")]]
            )
            user_state[uid] = {"step": "main_menu", "mode": "link"}
            return
    
    # ── Handle tool modes ──
    if st["step"] == "main_menu":
        return await event.respond(
            "**⚡ VORTEX PREMIUM v5.0**\n\nChoose your option below:",
            buttons=make_plan_buttons()
        )
    
    if st["mode"] == "link":
        if st["step"] == "link":
            if "uidb36=" not in txt:
                return await event.respond("**❌ Invalid!** Send Valid link with `uidb36=`")
            user_state[uid] = {"step":"pass","mode":"link","link":txt}
            await event.respond("**✅ Link saved!**\n\n**🔑 Now send new password** (min 6 chars):",buttons=[[Button.inline("🔙 Back to Menu",b"back_menu")]])
        elif st["step"] == "pass":
            if len(txt) < 6:
                return await event.respond("**❌ Min 6 chars:**")
            user_state[uid] = {"step":"busy"}
            msg = await event.respond("**🔄 Resetting the password wait...**")
            try:
                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(executor, reset_pass, st["link"], txt)
                if res.get("success"):
                    await msg.edit(
                        "━━━━━━━━━━━━━━━━━\n"
                        "**✅ PASSWORD RESET SUCCESSFUL**\n"
                        "━━━━━━━━━━━━━━━━━\n\n"
                        f"**👤 Username:** `{res['username']}`\n"
                        f"**🔑 New Password:** `{res['password']}`\n\n"
                        "━━━━━━━━━━━━━━━━━\n"
                        "**⚡ VORTEX PREMIUM v5.0**\n"
                        "By @dochains\n",
                        buttons=[[Button.inline("🔙 Back to Menu",b"back_menu")]]
                    )
                else:
                    await msg.edit(
                        "━━━━━━━━━━━━━━━━━\n"
                        "**❌ RESET FAILED**\n"
                        "━━━━━━━━━━━━━━━━━\n\n"
                        f"**Error:** `{res.get('error')}`\n\n",
                        buttons=[[Button.inline("🔙 Back to Menu",b"back_menu")]]
                    )
            except Exception as ex:
                await msg.edit(f"**❌ Error:** `{str(ex)}`\n",buttons=[[Button.inline("🔙 Back to Menu",b"back_menu")]])
            user_state[uid] = {"step":"main_menu","mode":"link"}
    
    elif st["mode"] == "recovery":
        if st["step"] == "recovery_username":
            user_state[uid] = {"step":"recovery_busy","mode":"recovery","target":txt}
            msg = await event.respond(f"**📧 Sending recovery to `{txt}`...**")
            try:
                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(executor, account_recovery, txt)
                if res.get("success"):
                    await msg.edit(
                        "━━━━━━━━━━━━━━━━━\n"
                        "**✅ RECOVERY SENT SUCCESSFULLY**\n"
                        "━━━━━━━━━━━━━━━━━\n\n"
                        f"**🎯 Target:** `{txt}`\n"
                        f"**📬 Check email/SMS for reset link**\n\n"
                        "━━━━━━━━━━━━━━━━━\n"
                        "**⚡ VORTEX PREMIUM v5.0**\n"
                        "By @dochains\n\n"
                        "**📤 Send another username or email:**\n"
                        "Or go back to menu",
                        buttons=[[Button.inline("🔙 Back to Menu",b"back_menu")]]
                    )
                    user_state[uid] = {"step":"recovery_username","mode":"recovery"}
                else:
                    await msg.edit(
                        "━━━━━━━━━━━━━━━━━\n"
                        "**❌ RECOVERY FAILED**\n"
                        "━━━━━━━━━━━━━━━━━\n\n"
                        f"**Error:** `{res.get('error')}`\n\n",
                        buttons=[[Button.inline("🔙 Back to Menu",b"back_menu")]]
                    )
                    user_state[uid] = {"step":"recovery_username","mode":"recovery"}
            except Exception as ex:
                await msg.edit(f"**❌ Error:** `{str(ex)}`\n",buttons=[[Button.inline("🔙 Back to Menu",b"back_menu")]])
                user_state[uid] = {"step":"recovery_username","mode":"recovery"}

# ─── Handle Photo/Screenshot for Payment Confirmation ────────────────────
@client.on(events.NewMessage)
async def dm_photo_handler(event):
    """Handle photo messages for payment screenshots."""
    if not event.is_private:
        return
    if not event.message.photo:
        return
    
    s = await event.get_sender()
    uid = s.id
    st = user_state.get(uid, {})
    
    if st.get("step") != "awaiting_screenshot":
        return
    
    # User sent a screenshot
    selected_plan = st.get("selected_plan")
    txn_id = st.get("txn_id", "N/A")
    plan = SUBSCRIPTION_PLANS.get(selected_plan, {})
    
    # Generate a unique payment ID
    payment_id = f"PAY_{int(time.time())}_{uid}"
    
    # Store in pending payments
    pending_payments[payment_id] = {
        "user_id": uid,
        "plan": selected_plan,
        "plan_label": plan.get("label", "Unknown"),
        "amount": plan.get("price", 0),
        "txn_id": txn_id,
        "timestamp": datetime.now().isoformat(),
        "status": "pending"
    }
    save_pending_payments()
    
    user_state[uid] = {"step": "main_menu", "mode": "link", "pending_payment_id": payment_id}
    
    await event.respond(
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**✅ PAYMENT SUBMITTED!**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**📋 Payment ID:** `{payment_id}`\n"
        f"**📌 Plan:** {plan.get('label', 'Unknown')}\n"
        f"**💰 Amount:** ₹{plan.get('price', 0)}\n"
        f"**🔢 Txn ID:** `{txn_id}`\n\n"
        "⏳ **Your payment is pending admin approval.**\n"
        "You will be notified once approved or rejected.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**⚡ VORTEX PREMIUM v5.0**",
        buttons=[[Button.inline("🔙 Back to Menu", b"back_menu")]]
    )
    
    # Forward to all admins
    for admin_id in ADMIN_IDS:
        try:
            # Forward the screenshot
            await client.send_message(admin_id, event.message)
            await client.send_message(
                admin_id,
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**🆕 NEW PAYMENT PENDING**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"**👤 User ID:** `{uid}`\n"
                f"**📌 Plan:** {plan.get('label', 'Unknown')}\n"
                f"**💰 Amount:** ₹{plan.get('price', 0)}\n"
                f"**🔢 Txn ID:** `{txn_id}`\n"
                f"**🆔 Payment ID:** `{payment_id}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**Actions:**\n"
                f"➡️ Approve: `/approve {uid}`\n"
                f"➡️ Reject: `/reject {payment_id} <reason>`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━"
            )
        except Exception as e:
            print(f"{Z}[!] Failed to notify admin {admin_id}: {e}{N}")

# ═══════════════════════════════════════════════════════════════════════════
# PART 4 - ADMIN COMMANDS (Telethon DM)
# ═══════════════════════════════════════════════════════════════════════════

@client.on(events.NewMessage(pattern="/approve"))
async def approve_cmd(event):
    s = await event.get_sender()
    if s.id not in ADMIN_IDS:
        return await event.respond("**⛔ UNAUTHORIZED**")
    if not event.is_private:
        return
    
    parts = event.message.text.strip().split()
    if len(parts) < 2:
        return await event.respond("**Usage:** `/approve <user_id>`\nor `/approve <user_id> permanent` (for permanent access)")
    
    try:
        target_uid = int(parts[1])
    except ValueError:
        return await event.respond("**❌ Invalid user ID**")
    
    # Determine plan
    if len(parts) >= 3 and parts[2].lower() == "permanent":
        plan_key = "permanent"
    else:
        # Check pending payments for this user
        user_payments = [pid for pid, p in pending_payments.items() if p.get("user_id") == target_uid and p.get("status") == "pending"]
        
        # Also try to get from the last known state or default to 7days
        plan_key = "7days"  # default
        if user_payments:
            latest = max(user_payments, key=lambda pid: pending_payments[pid].get("timestamp", ""))
            plan_key = pending_payments[latest].get("plan", "7days")
    
    if activate_subscription(target_uid, plan_key):
        plan_label = SUBSCRIPTION_PLANS[plan_key]["label"]
        plan_price = SUBSCRIPTION_PLANS[plan_key]["price_display"]
        
        await event.respond(
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**✅ SUBSCRIPTION APPROVED**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**👤 User ID:** `{target_uid}`\n"
            f"**📌 Plan:** {plan_label}\n"
            f"**💰 Amount:** {plan_price}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        # Mark pending payments as approved
        for pid in list(pending_payments.keys()):
            if pending_payments[pid].get("user_id") == target_uid and pending_payments[pid].get("status") == "pending":
                pending_payments[pid]["status"] = "approved"
        save_pending_payments()
        
        # Notify user
        try:
            expiry_msg = ""
            if plan_key != "permanent":
                sub = subscriptions.get(target_uid, {})
                if sub.get("expires_at"):
                    try:
                        exp = datetime.fromisoformat(sub["expires_at"])
                        expiry_msg = f"📅 **Expires:** {exp.strftime('%Y-%m-%d %H:%M')}\n"
                    except:
                        pass
            else:
                expiry_msg = "♾️ **Permanent Access**\n"
            
            await client.send_message(
                target_uid,
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**🎉 SUBSCRIPTION ACTIVE!**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"**✅ Your {plan_label} plan is now active!**\n\n"
                f"{expiry_msg}"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "**🔥 You can now use all VORTEX features:**\n"
                "🔐 Password Reset via Link\n"
                "📧 Account Recovery (Email/SMS)\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**⚡ VORTEX PREMIUM v5.0**\n"
                "By @dochains",
                buttons=make_plan_buttons()
            )
        except Exception as e:
            print(f"{Z}[!] Failed to notify user {target_uid}: {e}{N}")
    else:
        await event.respond("**❌ Failed to activate subscription**")


@client.on(events.NewMessage(pattern="/reject"))
async def reject_cmd(event):
    s = await event.get_sender()
    if s.id not in ADMIN_IDS:
        return await event.respond("**⛔ UNAUTHORIZED**")
    if not event.is_private:
        return
    
    parts = event.message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        return await event.respond("**Usage:** `/reject <payment_id> <reason>`\n\n**Pending Payments:**\n" + 
            "\n".join([f"• `{pid}` - User: `{p['user_id']}` - {p.get('plan_label', '?')} - ₹{p.get('amount', 0)}" 
                      for pid, p in pending_payments.items() if p.get("status") == "pending"]))
    
    payment_id = parts[1]
    reason = parts[2]
    
    if payment_id not in pending_payments:
        return await event.respond("**❌ Invalid payment ID**")
    
    pay_data = pending_payments[payment_id]
    pay_data["status"] = "rejected"
    pay_data["rejection_reason"] = reason
    save_pending_payments()
    
    target_uid = pay_data["user_id"]
    plan_label = pay_data.get("plan_label", "Unknown")
    
    await event.respond(
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**❌ PAYMENT REJECTED**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**🆔 Payment ID:** `{payment_id}`\n"
        f"**👤 User ID:** `{target_uid}`\n"
        f"**📌 Plan:** {plan_label}\n"
        f"**📝 Reason:** {reason}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    # Notify user
    try:
        await client.send_message(
            target_uid,
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**❌ PAYMENT REJECTED**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Your {plan_label} plan payment was rejected.**\n\n"
            f"**📝 Reason:** {reason}\n\n"
            "Please try again with correct payment details.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**⚡ VORTEX PREMIUM v5.0**",
            buttons=[[Button.inline("💳 SUBSCRIPTION PLANS", b"show_subscription")]]
        )
    except Exception as e:
        print(f"{Z}[!] Failed to notify user {target_uid}: {e}{N}")


@client.on(events.NewMessage(pattern="/mysub"))
async def mysub_cmd(event):
    """Check own subscription status."""
    s = await event.get_sender()
    uid = s.id
    if not event.is_private:
        return
    
    has_access, plan_info = check_subscription(uid)
    
    if uid in ADMIN_IDS:
        msg = (
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**👑 ADMIN ACCESS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "You have unlimited admin access.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━"
        )
    elif has_access:
        sub = subscriptions.get(uid, {})
        plan_key = sub.get("plan", "")
        plan = SUBSCRIPTION_PLANS.get(plan_key, {})
        expires = sub.get("expires_at", "Never (Permanent)")
        
        msg = (
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**✅ SUBSCRIPTION ACTIVE**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**📌 Plan:** {plan.get('label', plan_key)}\n"
            f"**📅 Expires:** {expires}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**⚡ VORTEX PREMIUM v5.0**"
        )
    else:
        msg = (
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**❌ NO ACTIVE SUBSCRIPTION**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "You don't have an active subscription.\n"
            "💳 Subscribe to access VORTEX features.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    await event.respond(msg, buttons=[[Button.inline("💳 SUBSCRIPTION PLANS", b"show_subscription")]])


# ─── Existing Admin Commands ────────────────────────────────────────────────

@client.on(events.NewMessage(pattern="/addchannel"))
async def add_ch(event):
    s = await event.get_sender()
    if s.id not in ADMIN_IDS: return await event.respond("**⛔ UNAUTHORIZED**")
    if not event.is_private: return
    parts = event.message.text.strip().split(maxsplit=3)
    if len(parts) < 3: return await event.respond("Usage: `/addchannel <invite_link> <@username>`\nor `/addchannel <invite_link> <@username> private`")
    link = parts[1]; uname = "@" + parts[2].lstrip("@")
    typ = "private" if (len(parts) > 3 and parts[3].lower() == "private") else "public"
    nxt = max(CHANNELS.keys()) + 1 if CHANNELS else 1
    CHANNELS[nxt] = {"type": typ, "link": link, "username": uname, "invite_link": link}
    save_channels()
    await event.respond(f"**✅ Channel {nxt} Added** ({typ})\n{uname}")

@client.on(events.NewMessage(pattern="/rmchannel"))
async def rm_ch(event):
    s = await event.get_sender()
    if s.id not in ADMIN_IDS: return await event.respond("**⛔ UNAUTHORIZED**")
    if not event.is_private: return
    parts = event.message.text.strip().split()
    if len(parts) < 2:
        cl = "\n".join([f"  {k}: {v['username']}" for k,v in CHANNELS.items()])
        return await event.respond(f"Usage: `/rmchannel <n>`\n\nCurrent:\n{cl}")
    try: idx = int(parts[1]); rem = CHANNELS.pop(idx); save_channels(); await event.respond(f"**✅ Removed Ch {idx}:** {rem['username']}")
    except: await event.respond("**❌ Invalid number**")

@client.on(events.NewMessage(pattern="/channels"))
async def list_ch(event):
    s = await event.get_sender()
    if s.id not in ADMIN_IDS: return await event.respond("**⛔ UNAUTHORIZED**")
    if not event.is_private: return
    if not CHANNELS: return await event.respond("No channels.")
    msg = "**📢 CHANNELS**\n\n"
    for idx,cd in sorted(CHANNELS.items()):
        ic = "🔒" if cd.get("type")=="private" else "📢"
        msg += f"{ic} **{idx}:** {cd['username']} ({cd.get('type','public')})\n   {cd['link']}\n\n"
    await event.respond(msg)

@client.on(events.NewMessage(pattern="/broadcast"))
async def broadcast_cmd(event):
    s = await event.get_sender()
    if s.id not in ADMIN_IDS: return await event.respond("**⛔ UNAUTHORIZED**")
    if not event.is_private: return
    parts = event.message.text.strip().split(maxsplit=1)
    if len(parts) < 2: return await event.respond(f"Usage: `/broadcast <message>`\n\nTotal users: {len(registered_users)}")
    msg_text = parts[1]; total = len(registered_users)
    if total == 0: return await event.respond("❌ No users.")
    await event.respond(f"**📤 Broadcasting to {total} users...**")
    sent = 0; failed = 0; failed_list = []
    status_msg = await event.respond(f"**📤 Progress:** 0/{total}")
    for uid, user_data in list(registered_users.items()):
        try:
            await client.send_message(int(uid), "━━━━━━━━━━━━━━━━━\n**📢 ADMIN BROADCAST**\n━━━━━━━━━━━━━━━━━\n\n" + f"{msg_text}\n\n━━━━━━━━━━━━━━━━━\n**⚡ VORTEX PREMIUM v5.0**")
            sent += 1
        except: failed += 1; failed_list.append(str(uid))
        if (sent + failed) % 5 == 0:
            try: await status_msg.edit(f"**📤 Progress:** {sent}/{total} | ❌ {failed}")
            except: pass
        await asyncio.sleep(0.05)
    result = "━━━━━━━━━━━━━━━━━\n**📢 BROADCAST COMPLETE**\n━━━━━━━━━━━━━━━━━\n\n" + f"✅ **Sent:** `{sent}`\n❌ **Failed:** `{failed}`\n👥 **Total:** `{total}`"
    if failed_list: result += f"\nFailed: `{', '.join(failed_list[:5])}`" + (f" +{len(failed_list)-5} more" if len(failed_list) > 5 else "")
    await status_msg.edit(result)

@client.on(events.NewMessage(pattern="/users"))
async def users_cmd(event):
    s = await event.get_sender()
    if s.id not in ADMIN_IDS: return await event.respond("**⛔ UNAUTHORIZED**")
    if not event.is_private: return
    total = len(registered_users)
    sub_count = len([u for u, s in subscriptions.items() if s.get("active")])
    
    msg = f"**👥 TOTAL USERS:** `{total}`\n**✅ SUBSCRIBED:** `{sub_count}`\n\n"
    if registered_users:
        sorted_users = sorted(registered_users.items(), key=lambda x: x[1].get("registered_at",""), reverse=True)
        for uid, data in sorted_users[:15]:
            uname = data.get("username","") or data.get("first_name","Unknown")
            reg = data.get("registered_at","")
            has_sub, pinfo = check_subscription(uid)
            sub_tag = "✅" if has_sub else "❌"
            msg += f"• {sub_tag} `{uid}` - @{uname}\n"
    await event.respond(msg)

@client.on(events.NewMessage(pattern="/set"))
async def set_ch(event):
    s = await event.get_sender()
    if s.id not in ADMIN_IDS: return await event.respond("**⛔ UNAUTHORIZED**")
    if not event.is_private: return
    cmd = event.message.text.strip().split()[0].lower()
    mp = {"/set":1,"/set2":2,"/set3":3}; idx = mp.get(cmd,0)
    if not idx: return
    parts = event.message.text.strip().split(maxsplit=2)
    if len(parts) < 3: return await event.respond(f"Usage: `{cmd} <link> <@username>`")
    CHANNELS[idx] = {"type":"public","link":parts[1],"username":"@"+parts[2].lstrip("@"),"invite_link":parts[1]}
    save_channels()
    await event.respond(f"**✅ Channel {idx} Updated**")


@client.on(events.NewMessage(pattern="/subs"))
async def subs_list_cmd(event):
    """List all active subscriptions."""
    s = await event.get_sender()
    if s.id not in ADMIN_IDS: return await event.respond("**⛔ UNAUTHORIZED**")
    if not event.is_private: return
    
    active_subs = {uid: sub for uid, sub in subscriptions.items() if sub.get("active")}
    
    msg = f"**📋 ACTIVE SUBSCRIPTIONS:** `{len(active_subs)}`\n\n"
    if active_subs:
        for uid, sub in sorted(active_subs.items(), key=lambda x: x[1].get("expires_at", ""), reverse=True):
            plan = sub.get("plan", "?")
            expires = sub.get("expires_at", "Permanent")
            uname = registered_users.get(uid, {}).get("username", "Unknown")
            msg += f"• `{uid}` - @{uname} - **{plan}** - Exp: {expires}\n"
    else:
        msg += "No active subscriptions.\n"
    
    # Pending payments
    pending = {pid: p for pid, p in pending_payments.items() if p.get("status") == "pending"}
    if pending:
        msg += f"\n**⏳ PENDING PAYMENTS:** `{len(pending)}`\n"
        for pid, p in pending.items():
            msg += f"• `{pid}` - User: `{p['user_id']}` - {p.get('plan_label', '?')} - ₹{p.get('amount', 0)}\n"
    
    await event.respond(msg)


@client.on(events.NewMessage(pattern="/revoke"))
async def revoke_cmd(event):
    """Revoke a user's subscription."""
    s = await event.get_sender()
    if s.id not in ADMIN_IDS: return await event.respond("**⛔ UNAUTHORIZED**")
    if not event.is_private: return
    
    parts = event.message.text.strip().split()
    if len(parts) < 2:
        return await event.respond("**Usage:** `/revoke <user_id>`")
    
    try:
        target_uid = int(parts[1])
    except ValueError:
        return await event.respond("**❌ Invalid user ID**")
    
    if target_uid in subscriptions:
        subscriptions[target_uid]["active"] = False
        save_subscriptions()
        await event.respond(f"**✅ Subscription revoked for `{target_uid}`**")
        
        try:
            await client.send_message(target_uid, 
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**⛔ SUBSCRIPTION REVOKED**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Your VORTEX Premium access has been revoked by admin.\n"
                "Contact support for more information.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**⚡ VORTEX PREMIUM v5.0**")
        except:
            pass
    else:
        await event.respond("**❌ No subscription found for this user**")


# ═══════════════════════════════════════════════════════════════════════════
# PART 5 - BOT API POLLING (GROUP MESSAGES) + MAIN
# ═══════════════════════════════════════════════════════════════════════════

# ─── BOT API POLLING THREAD (Group messages ke liye) ──────────────────────
def bot_api_polling():
    """Bot API se directly group messages read karega"""
    global last_update_id
    print(f"{G}[+] Bot API polling thread started for GROUP messages{N}")
    while True:
        try:
            params = {"timeout":30,"allowed_updates":["message","callback_query"]}
            if last_update_id: params["offset"] = last_update_id + 1
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",params=params,timeout=35)
            data = r.json()
            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    last_update_id = update["update_id"]
                    
                    if "callback_query" in update:
                        cb = update["callback_query"]
                        uid = cb["from"]["id"]
                        cb_data = cb["data"]
                        future = asyncio.run_coroutine_threadsafe(handle_bot_callback(uid,cb_data,cb),client.loop)
                        continue
                    
                    if "message" not in update: continue
                    msg = update["message"]
                    chat = msg.get("chat",{})
                    chat_type = chat.get("type","")
                    uid = msg["from"]["id"]
                    text = msg.get("text","")
                    
                    if chat_type not in ("group","supergroup"): continue
                    chat_id = chat["id"]
                    message_id = msg["message_id"]
                    username = msg["from"].get("username","")
                    first_name = msg["from"].get("first_name","")
                    print(f"{B}[BOT-API][GROUP] MSG from {uid} in {chat_id}: {(text or '(empty)')[:60]}{N}")
                    register_user(uid,username,first_name)
                    
                    if text.startswith("/"):
                        if text == "/start":
                            send_bot_message(chat_id,"**⚡ VORTEX PREMIUM v5.0**\n\n✅ **ACCESS GRANTED**\n\nPlease use /start in DM for full features.\n💳 Subscribe in DM to use tools.",message_id)
                            user_state[uid] = {"step":"main_menu","mode":"link"}
                        continue
                    
                    if "reply_to_message" in msg:
                        replied = msg["reply_to_message"]
                        original_id = replied["from"]["id"]
                        if original_id != uid and uid not in ADMIN_IDS:
                            send_bot_message(chat_id,"**⛔ This is not your message!**\n\n❌ You can only interact with your own requests.",message_id)
                            continue
                    
                    all_joined, nj = check_user_channels_sync(uid)
                    if not all_joined:
                        btn_msg = "⚠️ **VERIFICATION REQUIRED**\n\n"
                        for idx in nj:
                            cd = CHANNELS.get(idx,{})
                            btn_msg += f"❌ **Channel {idx}:** {cd.get('username','')}\n"
                        btn_msg += "\n**Join the channel and try again**"
                        send_bot_message(chat_id,btn_msg,message_id)
                        continue
                    
                    # Check subscription access for group tools
                    has_access, plan_info = check_subscription(uid)
                    if not has_access and uid not in ADMIN_IDS:
                        send_bot_message(chat_id,
                            "❌ **No Active Subscription!**\n\n"
                            "Please subscribe in DM to use VORTEX tools.\n"
                            "Send /start in DM to subscribe.",
                            message_id)
                        continue
                    
                    if uid not in user_state: user_state[uid] = {"step":"main_menu","mode":"link"}
                    st = user_state[uid]
                    
                    if uid not in user_state: user_state[uid] = {"step":"main_menu","mode":"link"}
                    st = user_state[uid]
                    
                    if st["step"] == "main_menu":
                        send_bot_message(chat_id,"**⚡ VORTEX PREMIUM v5.0**\n\nPlease use /start in DM for full features.",message_id)
                        continue
                    
                    if st["mode"] == "link":
                        if st["step"] == "link":
                            if "uidb36=" not in text:
                                send_bot_message(chat_id,"**❌ Invalid!** Send Valid link with `uidb36=`",message_id)
                                continue
                            user_state[uid] = {"step":"pass","mode":"link","link":text}
                            send_bot_message(chat_id,"**✅ Link saved!**\n\n**🔑 Now send new password** (min 6 chars):",message_id)
                        elif st["step"] == "pass":
                            if len(text) < 6:
                                send_bot_message(chat_id,"**❌ Min 6 chars:**",message_id)
                                continue
                            user_state[uid] = {"step":"busy"}
                            send_bot_message(chat_id,"**🔄 Resetting the password wait...**",message_id)
                            try:
                                res = reset_pass(st["link"],text)
                                if res.get("success"):
                                    send_bot_message(chat_id,"━━━━━━━━━━━━━━━━━\n**✅ PASSWORD RESET SUCCESSFUL**\n━━━━━━━━━━━━━━━━━\n\n" + f"**👤 Username:** `{res['username']}`\n**🔑 New Password:** `{res['password']}`\n\n" + "━━━━━━━━━━━━━━━━━\n**⚡ VORTEX PREMIUM v5.0**\nBy @dochains \n\nSend Another Valid Reset Link")
                                else:
                                    send_bot_message(chat_id,"━━━━━━━━━━━━━━━━━\n**❌ RESET FAILED**\n━━━━━━━━━━━━━━━━━\n\n" + f"**Error:** `{res.get('error')}`\n\nSend /start to retry")
                            except Exception as ex:
                                send_bot_message(chat_id,f"**❌ Error:** `{str(ex)}`")
                            user_state[uid] = {"step":"main_menu","mode":"link"}
                    
                    elif st["mode"] == "recovery":
                        if st["step"] == "recovery_username":
                            user_state[uid] = {"step":"recovery_busy","mode":"recovery","target":text}
                            send_bot_message(chat_id,f"**📧 Sending recovery to `{text}`...**",message_id)
                            try:
                                res = account_recovery(text)
                                if res.get("success"):
                                    send_bot_message(chat_id,"━━━━━━━━━━━━━━━━━\n**✅ RECOVERY SENT SUCCESSFULLY**\n━━━━━━━━━━━━━━━━━\n\n" + f"**🎯 Target:** `{text}`\n**📬 Check email/SMS for reset link**\n\n" + "━━━━━━━━━━━━━━━━━\n**⚡ VORTEX PREMIUM v5.0**\nBy @dochains \n\nSend another username/email or /start")
                                else:
                                    send_bot_message(chat_id,"━━━━━━━━━━━━━━━━━\n**❌ RECOVERY FAILED**\n━━━━━━━━━━━━━━━━━\n\n" + f"**Error:** `{res.get('error')}`\n\nSend /start to retry")
                            except Exception as ex:
                                send_bot_message(chat_id,f"**❌ Error:** `{str(ex)}`")
                            user_state[uid] = {"step":"main_menu","mode":"recovery"}
        except Exception as e:
            print(f"{Z}[!] Bot API polling error: {e}{N}")
            time.sleep(1)

def send_bot_message(chat_id, text, reply_to=None):
    try:
        data = {"chat_id":chat_id,"text":text,"parse_mode":"Markdown"}
        if reply_to: data["reply_to_message_id"] = reply_to
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json=data,timeout=5)
    except: pass

async def handle_bot_callback(uid, cb_data, cb_data_full):
    try:
        msg = cb_data_full.get("message",{})
        chat_id = msg.get("chat",{}).get("id",0)
        message_id = msg.get("message_id",0)
        
        if cb_data == "joined":
            all_joined, nj = check_user_channels_sync(uid)
            if all_joined:
                user_state[uid] = {"step":"main_menu","mode":"link"}
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={
                    "chat_id":chat_id,"message_id":message_id,
                    "text":"━━━━━━━━━━━━━━━━━━━━━━━\n**⚡ VORTEX PREMIUM v5.0**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n👋 **Welcome to VORTEX Premium!**\n\n🔐 **Instagram Account Recovery Tool**\n\n➡️ **Choose a mode below** to get started\n💳 **Subscribe** for unlimited access\n\n━━━━━━━━━━━━━━━━━━━━━━━\n**⚡ By @dochains**",
                    "parse_mode":"Markdown",
                    "reply_markup":{"inline_keyboard":[
                        [{"text":"🔐 RESET VIA LINK","callback_data":"mode_link"}],
                        [{"text":"📧 RECOVERY (Email/SMS)","callback_data":"mode_recovery"}],
                        [{"text":"💳 SUBSCRIPTION PLANS","callback_data":"show_subscription"}]
                    ]}},timeout=5)
            else:
                msg_text = "❌ **NOT VERIFIED**\n\n"
                for idx in nj:
                    cd = CHANNELS.get(idx,{})
                    msg_text += f"❌ **Channel {idx}:** {cd.get('username','')}\n"
                msg_text += "\nJoin and try again"
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":chat_id,"message_id":message_id,"text":msg_text,"parse_mode":"Markdown"},timeout=5)
            return
        
        # Handle subscription callbacks in group too
        if cb_data in ("mode_link", "mode_recovery", "show_subscription", "back_menu",
                       "sub_1day", "sub_7days", "sub_1month", "sub_permanent", "paid_confirm"):
            # Redirect to DM
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={
                "chat_id":uid,
                "text":"**⚡ VORTEX PREMIUM v5.0**\n\nPlease use the bot in DM for this feature.\nSend /start in DM.",
                "parse_mode":"Markdown"
            },timeout=5)
            return
        
        if cb_data == "back_menu":
            user_state[uid] = {"step":"main_menu","mode":"link"}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={
                "chat_id":chat_id,"message_id":message_id,
                "text":"**⚡ VORTEX PREMIUM v5.0**\n\nChoose your option:",
                "parse_mode":"Markdown",
                "reply_markup":{"inline_keyboard":[
                    [{"text":"🔐 RESET VIA LINK","callback_data":"mode_link"}],
                    [{"text":"📧 RECOVERY (Email/SMS)","callback_data":"mode_recovery"}],
                    [{"text":"💳 SUBSCRIPTION PLANS","callback_data":"show_subscription"}]
                ]}},timeout=5)
    except Exception as e:
        print(f"{Z}[!] Callback error: {e}{N}")

# ═══════════════════════════════════════════════════════════════════════════
# MAIN - START EVERYTHING
# ═══════════════════════════════════════════════════════════════════════════

polling_thread = threading.Thread(target=bot_api_polling, daemon=True)
polling_thread.start()

if __name__ == "__main__":
    print(f"{G}{'='*60}{N}")
    print(f"{G}[+] VORTEX PREMIUM v5.0 - WITH SUBSCRIPTION SYSTEM{N}")
    print(f"{G}[+] GROUP mode: Bot API Polling (direct){N}")
    print(f"{G}[+] DM mode: Telethon events{N}")
    print(f"{G}[+] Both work independently!{N}")
    print(f"{G}[+] Channels: {len(CHANNELS)}{N}")
    for idx,cd in sorted(CHANNELS.items()): print(f"    Ch {idx}: {cd['username']}")
    print(f"{G}[+] Registered users: {len(registered_users)}{N}")
    print(f"{G}[+] Active subscriptions: {len([u for u,s in subscriptions.items() if s.get('active')])}{N}")
    print(f"{G}[+] Pending payments: {len([p for p in pending_payments.values() if p.get('status')=='pending'])}{N}")
    print(f"{G}[+] Subscription plans loaded:{N}")
    for pk, pl in SUBSCRIPTION_PLANS.items():
        print(f"    {pl['label']:12s} → {pl['price_display']:>6s}")
    print(f"{G}[+] UPI: {UPI_ID}{N}")
    print(f"{G}[+] Admin commands: /approve <user_id>, /reject <pay_id> <reason>, /revoke <user_id>, /subs{N}")
    print(f"{G}[+] 2 MODES:{N}")
    print(f"{G}    1. 🔐 Reset via Link (uidb36 reset){N}")
    print(f"{G}    2. 📧 Recovery (Email/SMS trigger){N}")
    print(f"{G}{'='*60}{N}")
    try:
        client.run_until_disconnected()
    except KeyboardInterrupt:
        print(f"\n{Z}[-] Stopped{N}")
    except Exception as e:
        print(f"\n{Z}[-] Error: {e}{N}")