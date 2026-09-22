import os, time, json, sqlite3, requests, telebot, glob, random, threading
from telebot import types
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from datetime import date, datetime, timedelta

TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")
CHANNEL = os.getenv("CHANNEL", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DATA_DIR = os.getenv("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "kamo.db")
COINS_PATH = os.path.join(DATA_DIR, "coins.json")
DAILY_PATH = os.path.join(DATA_DIR, "daily.json")
INVITES_PATH = os.path.join(DATA_DIR, "invites.json")
PROFILES_PATH = os.path.join(DATA_DIR, "full_profiles.json")
GIFT_PATH = os.path.join(DATA_DIR, "gift_codes.json")
INVITE_USED_PATH = os.path.join(DATA_DIR, "invite_used.json")
WHEEL_PATH = os.path.join(DATA_DIR, "wheel.json")
VIP_PATH = os.path.join(DATA_DIR, "vip.json")
LASTSEEN_PATH = os.path.join(DATA_DIR, "lastseen.json")

bot = telebot.TeleBot(TOKEN)
try: requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook", timeout=10)
except: pass

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, mode TEXT, personality TEXT, history TEXT)")
conn.commit()

coins_db={}
if os.path.exists(COINS_PATH):
    try: coins_db=json.loads(open(COINS_PATH,"r").read())
    except: coins_db={}
def save_coins(): open(COINS_PATH,"w").write(json.dumps(coins_db))
def get_coins(uid): return coins_db.get(str(uid),15)
def add_coins(uid,n): coins_db[str(uid)]=get_coins(uid)+n; save_coins()
daily_db={}
if os.path.exists(DAILY_PATH):
    try: daily_db=json.loads(open(DAILY_PATH,"r").read())
    except: daily_db={}
def save_daily(): open(DAILY_PATH,"w").write(json.dumps(daily_db))
invites_db={}
if os.path.exists(INVITES_PATH):
    try: invites_db=json.loads(open(INVITES_PATH,"r").read())
    except: invites_db={}
def save_invites(): open(INVITES_PATH,"w").write(json.dumps(invites_db))
def get_invites(uid): return invites_db.get(str(uid),0)
def add_invite(uid): invites_db[str(uid)]=get_invites(uid)+1; save_invites()
invite_used={}
if os.path.exists(INVITE_USED_PATH):
    try: invite_used=json.loads(open(INVITE_USED_PATH,"r").read())
    except: invite_used={}
def save_invite_used(): open(INVITE_USED_PATH,"w").write(json.dumps(invite_used))

# NEW V8.4.0
wheel_db={}
if os.path.exists(WHEEL_PATH):
    try: wheel_db=json.loads(open(WHEEL_PATH,"r").read())
    except: wheel_db={}
def save_wheel(): open(WHEEL_PATH,"w").write(json.dumps(wheel_db))
vip_db={}
if os.path.exists(VIP_PATH):
    try: vip_db=json.loads(open(VIP_PATH,"r").read())
    except: vip_db={}
def save_vip(): open(VIP_PATH,"w").write(json.dumps(vip_db))
def is_vip(uid):
    if str(uid) in vip_db and time.time() < vip_db[str(uid)]: return True
    return False
def vip_left(uid):
    if str(uid) in vip_db:
        left=int(vip_db[str(uid)]-time.time())
        if left>0: return f"{left//86400} روز و {(left%86400)//3600} ساعت"
    return "0"

lastseen={}
if os.path.exists(LASTSEEN_PATH):
    try: lastseen=json.loads(open(LASTSEEN_PATH,"r").read())
    except: lastseen={}
def save_lastseen(): open(LASTSEEN_PATH,"w").write(json.dumps(lastseen))

reports_db={}; banned_until={}; spam_warnings={}; gift_tries={}
waiting=[]; chats={}; pending_coin_target={}; pending_rating={}

def is_link_spam(text):
    t=text.lower()
    bad=["http://","https://","t.me/","@","instagram.com","youtube.com",".ir",".com",".net",".org"]
    return any(x in t for x in bad)
def is_banned(uid):
    if str(uid) in banned_until:
        if time.time() < banned_until[str(uid)]: return True
        else: del banned_until[str(uid)]
    return False
def get_ban_time_left(uid):
    if str(uid) in banned_until:
        left = int(banned_until[str(uid)] - time.time())
        if left > 0:
            m = left // 60
            s = left % 60
            if m > 0: return f"{m} دقیقه و {s} ثانیه"
            else: return f"{s} ثانیه"
    return "0"
full_profiles={}
if os.path.exists(PROFILES_PATH):
    try: full_profiles=json.loads(open(PROFILES_PATH,"r",encoding="utf-8").read())
    except: full_profiles={}
def save_full(): open(PROFILES_PATH,"w",encoding="utf-8").write(json.dumps(full_profiles,ensure_ascii=False))
def get_full(uid):
    default={"name":"❓","gender":"❓","age":"❓","province":"❓","city":"❓","bio":"هنوز بیو ننوشتی","photo":None,"score":0,"relationship":"❓"}
    d=full_profiles.get(str(uid),default)
    if "name" not in d: d["name"]="❓"
    if "relationship" not in d: d["relationship"]="❓"
    return d
provinces=["تهران","اصفهان","مشهد","شیراز","تبریز","کرج","اهواز","قم","کرمانشاه","ارومیه","رشت","زاهدان","همدان","کرمان","یزد","اردبیل","بندرعباس","اراک","زنجان","گرگان","ساری","بوشهر","قزوین","سنندج","خرم آباد","ایلام","یاسوج","شهرکرد","بیرجند","بجنورد","سمنان"]
gift_db={}
if os.path.exists(GIFT_PATH):
    try: gift_db=json.loads(open(GIFT_PATH,"r",encoding="utf-8").read())
    except: gift_db={}
def save_gift(): open(GIFT_PATH,"w",encoding="utf-8").write(json.dumps(gift_db,ensure_ascii=False))
def is_admin(uid): return int(uid)==ADMIN_ID or str(uid)==str(ADMIN_ID)
def admin_keyboard():
    m=types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("📊 آمار کامل",callback_data="admin_stats"),types.InlineKeyboardButton("📢 پیام همگانی",callback_data="admin_broadcast"),types.InlineKeyboardButton("💰 سکه بده/بگیر",callback_data="admin_coins"),types.InlineKeyboardButton("🎁 ساخت کد هدیه",callback_data="admin_gift_make"),types.InlineKeyboardButton("🎁 لیست کدها",callback_data="admin_gift_list"),types.InlineKeyboardButton("🚫 بن / آنبن",callback_data="admin_ban"),types.InlineKeyboardButton("👤 اطلاعات کاربر",callback_data="admin_userinfo"),types.InlineKeyboardButton("🗑️ حذف کد هدیه",callback_data="admin_gift_del"),types.InlineKeyboardButton("⬅️ برگشت",callback_data="back"))
    return m
def get_user(uid):
    cur=conn.execute("SELECT mode, personality, history FROM users WHERE id=?",(uid,))
    row=cur.fetchone()
    if not row:
        conn.execute("INSERT INTO users VALUES (?,?,?,?)",(uid,"chat","funny","[]")); conn.commit()
        return "chat","funny",[]
    m,p,h=row
    try: h=json.loads(h)
    except: h=[]
    return m,p,h
def set_user(uid,mode=None,pers=None,hist=None):
    m,p,h=get_user(uid)
    if mode is not None: m=mode
    if pers is not None: p=pers
    if hist is not None: h=hist
    conn.execute("REPLACE INTO users VALUES (?,?,?,?)",(uid,m,p,json.dumps(h[-12:]))); conn.commit()
def ask_groq(uid,prompt,sys=None):
    _,pers,hist=get_user(uid)
    sys_map={"funny":"تو کامو هستی بامزه فارسی کوتاه","serious":"تو دستیار جدی دقیق هستی","romantic":"تو عاشقانه جواب میدی"}
    system=sys or sys_map.get(pers,sys_map["funny"])
    msgs=[{"role":"system","content":system}] + hist[-6:] + [{"role":"user","content":prompt}]
    models=["llama-3.1-8b-instant","llama-3.3-70b-versatile","openai/gpt-oss-20b"]
    for model in models:
        try:
            r=requests.post("https://api.groq.com/openai/v1/chat/completions",headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},json={"model":model,"messages":msgs,"max_tokens":1000,"temperature":0.8},timeout=35)
            if r.status_code==200:
                ans=r.json()["choices"][0]["message"]["content"]
                hist.append({"role":"user","content":prompt}); hist.append({"role":"assistant","content":ans})
                set_user(uid,hist=hist); return ans
        except: continue
    return "⚠️ سرور شلوغه، ۱۰ ثانیه بعد دوباره بفرست 🙏"
def transcribe(path):
    try:
        with open(path,'rb') as f:
            r=requests.post("https://api.groq.com/openai/v1/audio/transcriptions",headers={"Authorization":f"Bearer {GROQ_KEY}"},files={'file':f}, data={'model':'whisper-large-v3','language':'fa'}, timeout=60)
        if r.status_code==200: return r.json().get("text","")
    except: pass
    return None
def get_weather(city):
    try:
        geo=requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=fa&format=json",timeout=15).json()
        if "results" not in geo or not geo["results"]: return "شهر پیدا نشد ❌"
        lat,lon,name,country=geo["results"][0]["latitude"],geo["results"][0]["longitude"],geo["results"][0]["name"],geo["results"][0].get("country","")
        w=requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m,relative_humidity_2m",timeout=15).json()
        c=w['current']
        return f"🌤️ {name} {country}\n🌡️ دما: {c['temperature_2m']}°C\n💨 باد: {c['wind_speed_10m']} km/h\n💧 رطوبت: {c['relative_humidity_2m']}%"
    except Exception as e: return f"ارور هوا: {e}"
def make_card(text):
    W,H=1080,1080
    img=Image.new('RGB',(W,H),(20,20,35)); d=ImageDraw.Draw(img)
    for _ in range(5):
        x,y=random.randint(0,W),random.randint(0,H); r=random.randint(200,500)
        d.ellipse([x-r,y-r,x+r,y+r],fill=(random.randint(50,150),random.randint(50,150),random.randint(100,200)))
    try: font=ImageFont.truetype("DejaVuSans.ttf",55)
    except: font=ImageFont.load_default()
    d.rounded_rectangle([70,340,1010,740],radius=35,fill=(0,0,0,200))
    d.text((W//2,H//2),text[:100],font=font,fill="white",anchor="mm",align="center")
    p=os.path.join(DATA_DIR,"card.jpg"); img.save(p); return p
def make_profile(text):
    W,H=1080,1080
    img=Image.new('RGB',(W,H),(10,10,20)); d=ImageDraw.Draw(img)
    colors=[(255,0,150),(0,255,255),(255,255,0),(150,0,255)]
    for i in range(30):
        x,y=random.randint(0,W),random.randint(0,H); r=random.randint(50,250); c=random.choice(colors)
        d.ellipse([x-r,y-r,x+r,y+r],fill=c)
    overlay=Image.new('RGBA',(W,H),(0,0,0,180))
    img=Image.alpha_composite(img.convert('RGBA'),overlay).convert('RGB'); d=ImageDraw.Draw(img)
    try: font=ImageFont.truetype("DejaVuSans-Bold.ttf",110)
    except:
        try: font=ImageFont.truetype("DejaVuSans.ttf",100)
        except: font=ImageFont.load_default()
    for off in [(4,4),(-4,-4),(4,-4),(-4,4)]: d.text((W//2+off[0], H//2+off[1]), text[:15], font=font, fill=(255,0,200), anchor="mm")
    d.text((W//2,H//2), text[:15], font=font, fill="white", anchor="mm")
    p=os.path.join(DATA_DIR,"profile.jpg"); img.save(p); return p
def video_to_gif(in_path):
    try:
        import subprocess
        out=os.path.join(DATA_DIR,"out.gif")
        subprocess.run(["ffmpeg","-y","-i",in_path,"-t","5","-vf","fps=12,scale=480:-1:flags=lanczos",out], timeout=20, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(out): return out
    except: pass
    return None
def main_menu(uid):
    m=types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("🎨 عکس", callback_data="mode_image"),types.InlineKeyboardButton("📥 دانلود", callback_data="mode_download"),types.InlineKeyboardButton("💬 چت ناشناس", callback_data="chat"),types.InlineKeyboardButton("🎨 کارت ساز", callback_data="mode_card"),types.InlineKeyboardButton("👑 پروفایل گیمینگ", callback_data="mode_profile"),types.InlineKeyboardButton("🎞️ گیف ساز", callback_data="mode_gif"),types.InlineKeyboardButton("👤 پروفایل من", callback_data="full_profile"),types.InlineKeyboardButton("🎁 کد هدیه", callback_data="gift_redeem"),types.InlineKeyboardButton("🎡 گردونه", callback_data="wheel"),types.InlineKeyboardButton("💎 VIP", callback_data="vip_info"),types.InlineKeyboardButton("🎙️ ویس", callback_data="mode_voice"),types.InlineKeyboardButton("🌤️ هوا", callback_data="mode_weather"),types.InlineKeyboardButton("💰 سکه‌هام", callback_data="mycoins"),types.InlineKeyboardButton("🎁 روزانه", callback_data="daily"),types.InlineKeyboardButton("🏆 لیدربورد", callback_data="top"),types.InlineKeyboardButton("⚙️ همه امکانات", callback_data="more"),)
    if is_admin(uid): m.add(types.InlineKeyboardButton("👑 پنل مدیریت", callback_data="admin_panel"))
    return m
def more_menu():
    m=types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("📷 QR", callback_data="mode_qr"),types.InlineKeyboardButton("🌐 ترجمه", callback_data="mode_translate"),types.InlineKeyboardButton("🔗 خلاصه لینک", callback_data="mode_summarize"),types.InlineKeyboardButton("✍️ کپشن", callback_data="mode_caption"),types.InlineKeyboardButton("🔮 فال", callback_data="fal"),types.InlineKeyboardButton("😂 جوک", callback_data="joke"),types.InlineKeyboardButton("💵 قیمت BTC", callback_data="price"),types.InlineKeyboardButton("😎 شخصیت", callback_data="pers"),types.InlineKeyboardButton("👥 دعوت +10 سکه", callback_data="invite"),types.InlineKeyboardButton("🗑️ پاکسازی", callback_data="clear"),types.InlineKeyboardButton("⬅️ برگشت", callback_data="back"),)
    return m
def anon_keyboard():
    m=types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("👤 دیدن پروفایل", callback_data="view_partner"),types.InlineKeyboardButton("🚨 گزارش", callback_data="report_user"),types.InlineKeyboardButton("❌ پایان /end", callback_data="end_chat"))
    return m
def full_profile_keyboard():
    m=types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("📝 اسم",callback_data="edit_name"),types.InlineKeyboardButton("💍 وضعیت تاهل",callback_data="edit_relationship"),types.InlineKeyboardButton("👦👧 جنسیت",callback_data="edit_gender"),types.InlineKeyboardButton("🎂 سن",callback_data="edit_age"),types.InlineKeyboardButton("🗺️ استان",callback_data="edit_province"),types.InlineKeyboardButton("🏙️ شهر",callback_data="edit_city"),types.InlineKeyboardButton("📝 بیو",callback_data="edit_bio"),types.InlineKeyboardButton("📸 عکس پروفایل",callback_data="edit_photo"),types.InlineKeyboardButton("⬅️ برگشت",callback_data="back"))
    return m
def gender_keyboard():
    m=types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("👦 پسر",callback_data="set_gender_boy"),types.InlineKeyboardButton("👧 دختر",callback_data="set_gender_girl"))
    return m
def relationship_keyboard():
    m=types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("💙 مجرد",callback_data="set_rel_single"),types.InlineKeyboardButton("❤️ تو رابطه",callback_data="set_rel_taken"),types.InlineKeyboardButton("💍 متاهل",callback_data="set_rel_married"),types.InlineKeyboardButton("💔 طلاق گرفته",callback_data="set_rel_divorced"))
    return m
def chat_filter_keyboard():
    m=types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("👦 فقط پسر",callback_data="filter_boy"),types.InlineKeyboardButton("👧 فقط دختر",callback_data="filter_girl"),types.InlineKeyboardButton("👥 فرقی نمیکنه",callback_data="filter_any"))
    return m
def rating_keyboard():
    m=types.InlineKeyboardMarkup(row_width=5)
    m.add(types.InlineKeyboardButton("1⭐",callback_data="rate_1"),types.InlineKeyboardButton("2⭐",callback_data="rate_2"),types.InlineKeyboardButton("3⭐",callback_data="rate_3"),types.InlineKeyboardButton("4⭐",callback_data="rate_4"),types.InlineKeyboardButton("5⭐",callback_data="rate_5"),types.InlineKeyboardButton("⏭️ رد شدن",callback_data="rate_skip"))
    return m
def province_keyboard():
    m=types.InlineKeyboardMarkup(row_width=3)
    btns=[types.InlineKeyboardButton(p,callback_data=f"set_prov_{p}") for p in provinces[:18]]
    m.add(*btns)
    m.add(types.InlineKeyboardButton("بقیه استان‌ها دستی بنویس",callback_data="edit_province_manual"))
    return m

@bot.message_handler(commands=['start'])
def start_h(msg):
    uid=msg.chat.id
    lastseen[str(uid)]=time.time(); save_lastseen()
    if is_banned(uid):
        bot.send_message(uid,f"🚫 تو بن هستی!\n⏳ زمان باقی‌مانده: {get_ban_time_left(uid)}\nبعدا برگرد.")
        return
    args=msg.text.split()
    if len(args)>1 and args[1].isdigit() and args[1]!=str(uid):
        inviter=args[1]
        if str(uid) not in invite_used and str(uid) not in coins_db:
            add_coins(inviter,10); add_invite(inviter); save_invites()
            invite_used[str(uid)]=inviter; save_invite_used()
            coins_db[str(uid)]=15; save_coins()
            try: bot.send_message(int(inviter),f"🎉 یه نفر با لینکت اومد! +10 سکه گرفتی\n💰 سکه‌هات: {get_coins(inviter)}\n👥 دعوت‌ها: {get_invites(inviter)}")
            except: pass
    set_user(uid,mode="chat")
    coins=get_coins(uid)
    vip_tag="💎 VIP" if is_vip(uid) else ""
    bot.send_message(uid,f"سلام {msg.from_user.first_name} عزیز 👋✨ {vip_tag}\n\nبه کامو خوش اومدی!\n💰 سکه‌هات: {coins}\n👇 از منو یه گزینه انتخاب کن:",reply_markup=main_menu(uid))

def find_match(my_uid, my_want):
    my_profile=get_full(my_uid)
    my_gender=my_profile.get("gender","❓")
    # VIP ها اول
    vip_waiting=[w for w in waiting if is_vip(w["uid"])]
    normal_waiting=[w for w in waiting if not is_vip(w["uid"])]
    ordered = vip_waiting + normal_waiting if is_vip(my_uid) else waiting
    # اگه خودت VIP باشی، اول VIP ها رو چک کن
    search_list = ordered if is_vip(my_uid) else waiting
    for i, w in enumerate(search_list):
        # برای لیست اصلی index پیدا کن
        real_index = waiting.index(w) if w in waiting else -1
        if real_index==-1: continue
        other_uid=w["uid"]
        other_want=w["want"]
        if other_uid==my_uid: continue
        other_profile=get_full(other_uid)
        other_gender=other_profile.get("gender","❓")
        ok1 = True
        if my_want=="boy" and "پسر" not in other_gender: ok1=False
        if my_want=="girl" and "دختر" not in other_gender: ok1=False
        ok2 = True
        if other_want=="boy" and "پسر" not in my_gender: ok2=False
        if other_want=="girl" and "دختر" not in my_gender: ok2=False
        if ok1 and ok2:
            return waiting.pop(real_index)
    return None

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    uid=c.message.chat.id; data=c.data
    lastseen[str(uid)]=time.time(); save_lastseen()
    if is_banned(uid) and not is_admin(uid):
        bot.answer_callback_query(c.id, f"🚫 تو بن هستی! {get_ban_time_left(uid)} باقی مونده", show_alert=True)
        return
    if data.startswith("rate_"):
        partner = pending_rating.get(str(uid))
        if data=="rate_skip":
            bot.send_message(uid,"باشه رد شد ✅",reply_markup=main_menu(uid))
        else:
            try:
                stars=int(data.split("_")[1])
                pf=get_full(partner) if partner else None
                if pf:
                    pf['score']=pf.get('score',0)+stars
                    full_profiles[str(partner)]=pf; save_full()
                    bot.send_message(uid,f"✅ امتیاز {stars}⭐ ثبت شد!",reply_markup=main_menu(uid))
                    try: bot.send_message(int(partner),f"⭐ یکی بهت امتیاز {stars} داد! امتیاز کلت: {pf['score']}")
                    except: pass
                else:
                    bot.send_message(uid,"✅ ثبت شد",reply_markup=main_menu(uid))
            except: pass
        if str(uid) in pending_rating: del pending_rating[str(uid)]
        bot.answer_callback_query(c.id); return
    if data=="wheel":
        today=str(date.today())
        if wheel_db.get(str(uid))==today:
            bot.answer_callback_query(c.id,"🎡 امروز چرخوندی! فردا بیا",show_alert=True); return
        reward=random.choice([1,1,2,2,3,3,5,5,7,10,15])
        add_coins(uid,reward); wheel_db[str(uid)]=today; save_wheel()
        bot.send_message(uid,f"🎡 گردونه چرخید!\n\n🎉 {reward} سکه برنده شدی!\n💰 سکه‌هات: {get_coins(uid)}",reply_markup=main_menu(uid))
        bot.answer_callback_query(c.id); return
    if data=="vip_info":
        if is_vip(uid):
            bot.send_message(uid,f"💎 تو VIP هستی!\n⏳ باقی‌مانده: {vip_left(uid)}\n\nمزایا:\n✅ پروفایل طلایی\n✅ اولویت تو چت ناشناس\n✅ 2 برابر شانس گردونه",reply_markup=main_menu(uid))
        else:
            m=types.InlineKeyboardMarkup(); m.add(types.InlineKeyboardButton("💎 خرید VIP - 30 سکه / 7 روز",callback_data="buy_vip"))
            bot.send_message(uid,"💎 **پروفایل VIP**\n\nبا 30 سکه 7 روز VIP شو:\n🌟 پروفایل طلایی\n⚡ اولویت تو چت ناشناس\n🎡 شانس بیشتر تو گردونه\n\nمیخری؟",reply_markup=m)
        return
    if data=="buy_vip":
        if get_coins(uid)<30:
            bot.send_message(uid,f"💸 سکه‌ت کمه! 30 سکه لازمه، تو {get_coins(uid)} داری\nلینک دعوتت:\nhttps://t.me/{bot.get_me().username}?start={uid}"); return
        add_coins(uid,-30); vip_db[str(uid)]=time.time()+7*86400; save_vip()
        bot.send_message(uid,f"✅ تبریک! 7 روز VIP شدی 💎\n💰 سکه‌هات: {get_coins(uid)}",reply_markup=main_menu(uid))
        return
    if data=="report_user":
        if uid not in chats: bot.answer_callback_query(c.id,"تو تو چت نیستی"); return
        partner=chats[uid]
        reports_db[str(partner)]=reports_db.get(str(partner),0)+1
        if reports_db[str(partner)]>=2:
            banned_until[str(partner)]=time.time()+600
            try: bot.send_message(partner,f"🚫 به خاطر گزارش کاربران 10 دقیقه بن شدی\n⏳ زمان: 10 دقیقه")
            except: pass
        bot.send_message(uid,"✅ گزارش ثبت شد. چت بسته شد.",reply_markup=main_menu(uid))
        pending_rating[str(uid)]=partner
        bot.send_message(uid,"به این چت چه امتیازی میدی؟",reply_markup=rating_keyboard())
        if uid in chats:
            p=chats[uid]; del chats[uid]
            if p in chats: del chats[p]
            try: bot.send_message(p,"❌ طرف گزارشت کرد و چت بسته شد",reply_markup=main_menu(p))
            except: pass
        bot.answer_callback_query(c.id,"گزارش شد"); return
    if data=="end_chat":
        partner=None
        if uid in chats:
            partner=chats[uid]; del chats[uid]
            if partner in chats: del chats[partner]
            try: bot.send_message(partner,"❌ طرف چت رو بست\n/chat برای چت جدید",reply_markup=main_menu(partner))
            except: pass
            if partner:
                pending_rating[str(uid)]=partner
                pending_rating[str(partner)]=uid
                bot.send_message(uid,"چت بسته شد ❌\nبه طرف مقابل چه امتیازی میدی؟",reply_markup=rating_keyboard())
                try: bot.send_message(partner,"چت بسته شد ❌\nبه طرف مقابل چه امتیازی میدی؟",reply_markup=rating_keyboard())
                except: pass
        else:
            bot.send_message(uid,"چت بسته شد ❌",reply_markup=main_menu(uid))
        global waiting
        waiting=[w for w in waiting if w["uid"]!=uid]
        bot.answer_callback_query(c.id); return
    if data=="view_partner":
        if uid not in chats: bot.answer_callback_query(c.id,"تو تو چت نیستی"); return
        partner=chats[uid]
        pf=get_full(partner)
        vip_tag="💎 VIP\n" if is_vip(partner) else ""
        txt=f"{vip_tag}👤 پروفایل طرف مقابل:\n\n📝 اسم: {pf['name']}\n💍 وضعیت: {pf.get('relationship','❓')}\n👦👧 جنسیت: {pf['gender']}\n🎂 سن: {pf['age']}\n🗺️ استان: {pf['province']}\n🏙️ شهر: {pf['city']}\n📝 بیو: {pf['bio']}\n⭐ امتیاز: {pf['score']}"
        if pf['photo']:
            try: bot.send_photo(uid,pf['photo'],caption=txt); bot.answer_callback_query(c.id); return
            except: pass
        bot.send_message(uid,txt); bot.answer_callback_query(c.id); return
    if data=="full_profile":
        pf=get_full(uid)
        vip_tag="💎 VIP - " + vip_left(uid) + " باقی\n" if is_vip(uid) else ""
        txt=f"{vip_tag}👤 **پروفایل تو:**\n\n📝 اسم: {pf['name']}\n💍 وضعیت: {pf.get('relationship','❓')}\n👦👧 جنسیت: {pf['gender']}\n🎂 سن: {pf['age']}\n🗺️ استان: {pf['province']}\n🏙️ شهر: {pf['city']}\n📝 بیو: {pf['bio']}\n⭐ امتیاز: {pf['score']}\n💰 سکه: {get_coins(uid)}\n\nبرای ویرایش هر کدوم بزن:"
        if pf['photo']:
            try: bot.send_photo(uid,pf['photo'],caption=txt,reply_markup=full_profile_keyboard()); return
            except: pass
        bot.send_message(uid,txt,reply_markup=full_profile_keyboard()); return
    if data=="edit_name": set_user(uid,mode="edit_name"); bot.send_message(uid,"📝 اسمت رو بفرست (مثلا: علی):"); return
    if data=="edit_relationship": bot.send_message(uid,"💍 وضعیت تاهلت رو انتخاب کن:",reply_markup=relationship_keyboard()); return
    if data.startswith("set_rel_"):
        mapping={"single":"💙 مجرد","taken":"❤️ تو رابطه","married":"💍 متاهل","divorced":"💔 طلاق گرفته"}
        key=data.replace("set_rel_","")
        val=mapping.get(key,"❓")
        pf=get_full(uid); pf['relationship']=val; full_profiles[str(uid)]=pf; save_full()
        bot.send_message(uid,f"✅ وضعیت ثبت شد: {val}",reply_markup=full_profile_keyboard()); return
    if data=="edit_gender": bot.send_message(uid,"جنسیتت رو انتخاب کن:",reply_markup=gender_keyboard()); return
    if data.startswith("set_gender_"):
        g="👦 پسر" if "boy" in data else "👧 دختر"
        pf=get_full(uid); pf['gender']=g; full_profiles[str(uid)]=pf; save_full()
        bot.send_message(uid,f"✅ جنسیت ثبت شد: {g}",reply_markup=full_profile_keyboard()); return
    if data=="edit_age": set_user(uid,mode="edit_age"); bot.send_message(uid,"🎂 سنت رو بفرست (مثلا 22):"); return
    if data=="edit_province": bot.send_message(uid,"🗺️ استان رو انتخاب کن:",reply_markup=province_keyboard()); return
    if data.startswith("set_prov_"):
        prov=data.replace("set_prov_","")
        pf=get_full(uid); pf['province']=prov; full_profiles[str(uid)]=pf; save_full()
        bot.send_message(uid,f"✅ استان شد: {prov}\nحالا شهرت رو بفرست:",reply_markup=None)
        set_user(uid,mode="edit_city"); return
    if data=="edit_province_manual": set_user(uid,mode="edit_province"); bot.send_message(uid,"نام استان رو بنویس:"); return
    if data=="edit_city": set_user(uid,mode="edit_city"); bot.send_message(uid,"🏙️ نام شهرت رو بفرست:"); return
    if data=="edit_bio": set_user(uid,mode="edit_bio"); bot.send_message(uid,"📝 بیوت رو بنویس (مثلا: عاشق موسیقی):"); return
    if data=="edit_photo": set_user(uid,mode="edit_photo"); bot.send_message(uid,"📸 حالا عکس پروفایلت رو بفرست (به عنوان عکس):"); return
    if data=="admin_panel":
        if not is_admin(uid): bot.answer_callback_query(c.id,"⛔ دسترسی نداری"); return
        bot.send_message(uid,"👑 **پنل مدیریت حرفه‌ای کامو**",reply_markup=admin_keyboard()); return
    if data=="admin_stats":
        if not is_admin(uid): return
        total_users=len(coins_db); total_profiles=len(full_profiles); total_chats=len(chats); total_wait=len(waiting)
        total_coins=sum(coins_db.values()) if coins_db else 0
        txt=f"📊 **آمار ربات:**\n\n👥 کل کاربران: {total_users}\n👤 پروفایل کامل: {total_profiles}\n💬 چت فعال: {total_chats}\n⏳ تو صف: {total_wait}\n💰 مجموع سکه‌ها: {total_coins}\n🎁 کد هدیه فعال: {len(gift_db)}\n🚫 بن شده: {len(banned_until)}\n💎 VIP: {len([k for k in vip_db if is_vip(k)])}\n📂 دیتابیس: {DATA_DIR}"
        bot.send_message(uid,txt,reply_markup=admin_keyboard()); return
    if data=="admin_broadcast":
        if not is_admin(uid): return
        set_user(uid,mode="admin_broadcast"); bot.send_message(uid,"📢 متن پیام همگانی رو بفرست (به همه میره):"); return
    if data=="admin_coins":
        if not is_admin(uid): return
        set_user(uid,mode="admin_coins"); bot.send_message(uid,"💰 اول **آیدی عددی کاربر** رو بفرست:\nمثال: `373185491`",parse_mode="Markdown"); return
    if data=="admin_gift_make":
        if not is_admin(uid): return
        set_user(uid,mode="admin_gift_make"); bot.send_message(uid,"🎁 فرمت: `کد سکه تعداد`\nمثال: `WELCOME 10 100`"); return
    if data=="admin_gift_list":
        if not is_admin(uid): return
        if not gift_db: bot.send_message(uid,"هیچ کد فعالی نیست"); return
        txt="🎁 **لیست کدهای هدیه:**\n\n"
        for code,info in gift_db.items():
            used=len(info.get("used_by",[]))
            txt+=f"🔹 `{code}` - {info['coins']}🪙 - {used}/{info['max_uses']}\n"
        bot.send_message(uid,txt,parse_mode="Markdown"); return
    if data=="admin_gift_del":
        if not is_admin(uid): return
        set_user(uid,mode="admin_gift_del"); bot.send_message(uid,"نام کد رو برای حذف بفرست:"); return
    if data=="admin_ban":
        if not is_admin(uid): return
        set_user(uid,mode="admin_ban"); bot.send_message(uid,"🚫 فرمت: `آیدی دقیقه`\nمثال: `123456 60` = 60 دقیقه بن\n`123456 0` = آنبن"); return
    if data=="admin_userinfo":
        if not is_admin(uid): return
        set_user(uid,mode="admin_userinfo"); bot.send_message(uid,"👤 آیدی کاربر رو بفرست:"); return
    if data=="gift_redeem":
        gift_tries[str(uid)]=0
        set_user(uid,mode="gift_redeem"); bot.send_message(uid,"🎁 کد هدیه رو بفرست:"); return
    if data=="chat":
        if is_banned(uid): bot.send_message(uid,f"🚫 تو بن هستی!\n⏳ {get_ban_time_left(uid)} باقی مونده"); return
        if uid in chats: bot.send_message(uid,"تو الان تو چاتی! /end بزن",reply_markup=anon_keyboard()); return
        if any(w["uid"]==uid for w in waiting): bot.send_message(uid,"توی صفی... /end برای لغو"); return
        bot.send_message(uid,"👇 دوست داری با کی وصل شی؟",reply_markup=chat_filter_keyboard()); return
    if data.startswith("filter_"):
        want=data.replace("filter_","")
        if is_banned(uid): bot.send_message(uid,f"🚫 تو بن هستی!"); return
        match=find_match(uid,want)
        if match:
            p=match["uid"]
            chats[uid]=p; chats[p]=uid
            set_user(uid,mode="chat"); set_user(p,mode="chat")
            pf1=get_full(uid); pf2=get_full(p)
            vip1="💎" if is_vip(uid) else ""; vip2="💎" if is_vip(p) else ""
            info_p=f"👤 طرف: {pf2['name']} {vip2} | {pf2.get('relationship','❓')} | {pf2['gender']} | {pf2['age']} | {pf2['province']}-{pf2['city']}"
            info_u=f"👤 طرف: {pf1['name']} {vip1} | {pf1.get('relationship','❓')} | {pf1['gender']} | {pf1['age']} | {pf1['province']}-{pf1['city']}"
            bot.send_message(uid,f"✅ وصل شدی به یه ناشناس!\n{info_p}\n\nهر چی بفرستی میره\n🚨 لینک = بن",reply_markup=anon_keyboard())
            bot.send_message(p,f"✅ یه نفر وصل شد بهت!\n{info_u}\n\n🚨 لینک = بن",reply_markup=anon_keyboard())
        else:
            waiting.append({"uid":uid,"want":want})
            set_user(uid,mode="chat_waiting_ai")
            bot.send_message(uid,f"🔍 دنبال { 'پسر' if want=='boy' else 'دختر' if want=='girl' else 'یه نفر'} میگردم...\n\n💡 تا پیدا بشه من کامو هستم، باهام حرف بزن! هر چی بگی جواب میدم 🤖\n/end برای لغو")
        return
    if data=="more": bot.send_message(uid,"⚙️ همه امکانات کامو:",reply_markup=more_menu())
    elif data=="back": bot.send_message(uid,"منو اصلی:",reply_markup=main_menu(uid))
    elif data=="mycoins": bot.answer_callback_query(c.id, f"💰 سکه‌هات: {get_coins(uid)}", show_alert=True); return
    elif data=="daily":
        today=str(date.today()); last=daily_db.get(str(uid))
        if last==today: bot.answer_callback_query(c.id, "امروز گرفتی! فردا بیا 🎁", show_alert=True); return
        daily_db[str(uid)]=today; save_daily(); add_coins(uid,5)
        bot.answer_callback_query(c.id, f"🎁 5 سکه گرفتی! سکه‌هات: {get_coins(uid)}", show_alert=True)
        bot.send_message(uid, f"✅ 5 سکه روزانه گرفتی!\n💰 سکه‌هات: {get_coins(uid)}", reply_markup=main_menu(uid)); return
    elif data=="top":
        if not invites_db: top_text="هنوز کسی دعوت نکرده!"
        else:
            sorted_inv=sorted(invites_db.items(), key=lambda x: x[1], reverse=True)[:10]
            top_text="🏆 **برترین دعوت‌کنندگان:**\n\n"
            for i,(u,cnt) in enumerate(sorted_inv,1): top_text+=f"{i}. {u} - {cnt} دعوت\n"
            top_text+=f"\n👤 دعوت‌های تو: {get_invites(uid)}"
        bot.send_message(uid,top_text)
    elif data=="invite": bot.send_message(uid,f"👥 لینک دعوتت (هر نفر +10 سکه):\nhttps://t.me/{bot.get_me().username}?start={uid}\n\nدعوت‌هات: {get_invites(uid)}")
    elif data=="clear": set_user(uid,hist=[]); bot.send_message(uid,"حافظه چت پاک شد 🗑️")
    elif data=="pers":
        m=types.InlineKeyboardMarkup(); m.add(types.InlineKeyboardButton("😂 بامزه",callback_data="pers_funny"),types.InlineKeyboardButton("🧐 جدی",callback_data="pers_serious"),types.InlineKeyboardButton("❤️ عاشقانه",callback_data="pers_romantic"))
        bot.send_message(uid,"چه شخصیتی دوست داری؟",reply_markup=m)
    elif data.startswith("pers_"): set_user(uid,pers=data.replace("pers_","")); bot.send_message(uid,f"شخصیت شد {data.replace('pers_','')} ✅",reply_markup=main_menu(uid))
    elif data=="fal": bot.send_chat_action(uid,'typing'); txt=ask_groq(uid,"فال حافظ واقعی بده: غزل + معنی کوتاه","تو حافظ هستی"); bot.send_message(uid,txt)
    elif data=="joke": bot.send_chat_action(uid,'typing'); txt=ask_groq(uid,"جوک فارسی جدید خنده دار کوتاه","جوک گو"); bot.send_message(uid,txt)
    elif data=="price":
        try:
            r=requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",timeout=10).json()
            bot.send_message(uid,f"₿ BTC: ${r['bitcoin']['usd']}")
        except: bot.send_message(uid,"ارور قیمت")
    elif data.startswith("mode_"):
        set_user(uid,mode=data.replace("mode_",""))
        txts={"image":"چی بسازم؟ (1🪙)","download":"لینک Insta/YT/TikTok بفرست (1🪙)","weather":"اسم شهر رو بفرست؟ مثلا تبریز","voice":"متن بفرست ویس کنم یا ویس بفرست متن کنم","qr":"متن یا لینک برای QR بفرست؟","translate":"متنت رو برای ترجمه بفرست 🌐","summarize":"لینک مقاله یا سایت رو بفرست تا خلاصه کنم 🔗","caption":"موضوع کپشن رو بفرست؟","card":"متن کارتت رو بفرست؟ مثلا: تولدت مبارک علی ❤️ (1🪙)","profile":"اسم پروفایل گیمینگت رو بفرست 👑 مثلا: KAMO (1🪙)","gif":"ویدیوت رو بفرست تا گیفش کنم 🎞️ (1🪙)"}
        bot.send_message(uid,txts.get(data.replace("mode_",""),"بفرست:"))
    try: bot.answer_callback_query(c.id)
    except: pass

@bot.message_handler(commands=['end','next','chat','menu','coins','daily','top','report','profile','admin','gift','spin','vip'])
def cmds(msg):
    uid=msg.chat.id
    lastseen[str(uid)]=time.time(); save_lastseen()
    if is_banned(uid) and not is_admin(uid):
        bot.send_message(uid,f"🚫 تو بن هستی!\n⏳ زمان باقی‌مانده: {get_ban_time_left(uid)}")
        return
    t=msg.text.lower(); parts=msg.text.split()
    if "spin" in t or "گردونه" in t:
        today=str(date.today())
        if wheel_db.get(str(uid))==today: bot.send_message(uid,"🎡 امروز چرخوندی! فردا بیا"); return
        reward=random.choice([1,1,2,2,2,3,3,5,5,7,10,15])
        if is_vip(uid): reward*=2
        add_coins(uid,reward); wheel_db[str(uid)]=today; save_wheel()
        bot.send_message(uid,f"🎡 گردونه چرخید!\n\n🎉 {reward} سکه برنده شدی! {'💎 VIP 2x' if is_vip(uid) else ''}\n💰 سکه‌هات: {get_coins(uid)}",reply_markup=main_menu(uid)); return
    if "vip" in t:
        if is_vip(uid): bot.send_message(uid,f"💎 VIP هستی! باقی: {vip_left(uid)}"); return
        else:
            m=types.InlineKeyboardMarkup(); m.add(types.InlineKeyboardButton("💎 خرید VIP - 30 سکه",callback_data="buy_vip"))
            bot.send_message(uid,"💎 VIP 30 سکه / 7 روز",reply_markup=m); return
    if "admin" in t:
        if not is_admin(uid): bot.send_message(uid,"⛔ تو ادمین نیستی"); return
        bot.send_message(uid,"👑 پنل مدیریت:",reply_markup=admin_keyboard()); return
    if "gift" in t:
        if len(parts)>=2:
            code=parts[1].upper().strip()
            if code not in gift_db: bot.send_message(uid,"❌ کد اشتباهه یا منقضی شده"); return
            info=gift_db[code]
            if str(uid) in info.get("used_by",[]): bot.send_message(uid,"⚠️ قبلا از این کد استفاده کردی!"); return
            if len(info.get("used_by",[]))>=info['max_uses']: bot.send_message(uid,"❌ ظرفیت این کد تموم شده"); return
            add_coins(uid,info['coins']); info.setdefault("used_by",[]).append(str(uid)); save_gift()
            bot.send_message(uid,f"🎉 تبریک! {info['coins']} سکه گرفتی!\n💰 سکه‌هات: {get_coins(uid)}",reply_markup=main_menu(uid)); return
        else:
            gift_tries[str(uid)]=0
            set_user(uid,mode="gift_redeem"); bot.send_message(uid,"🎁 کد هدیه رو بفرست:"); return
    if "menu" in t: bot.send_message(uid,"منو:",reply_markup=main_menu(uid)); return
    if "coins" in t: bot.send_message(uid,f"💰 سکه‌هات: {get_coins(uid)}"); return
    if "profile" in t:
        pf=get_full(uid)
        vip_tag="💎 VIP\n" if is_vip(uid) else ""
        txt=f"{vip_tag}👤 پروفایل:\n📝 اسم: {pf['name']}\n💍 وضعیت: {pf.get('relationship','❓')}\nجنسیت: {pf['gender']}\nسن: {pf['age']}\nاستان: {pf['province']}\nشهر: {pf['city']}\nبیو: {pf['bio']}\n⭐ امتیاز: {pf['score']}"
        if pf['photo']:
            try: bot.send_photo(uid,pf['photo'],caption=txt,reply_markup=full_profile_keyboard()); return
            except: pass
        bot.send_message(uid,txt,reply_markup=full_profile_keyboard()); return
    if "daily" in t:
        today=str(date.today()); last=daily_db.get(str(uid))
        if last==today: bot.send_message(uid,"امروز گرفتی! فردا بیا 🎁"); return
        daily_db[str(uid)]=today; save_daily(); add_coins(uid,5)
        bot.send_message(uid,f"🎁 5 سکه روزانه گرفتی!\n💰 سکه‌هات: {get_coins(uid)}",reply_markup=main_menu(uid)); return
    if "top" in t:
        if not invites_db: bot.send_message(uid,"هنوز کسی دعوت نکرده!"); return
        sorted_inv=sorted(invites_db.items(), key=lambda x: x[1], reverse=True)[:10]
        top_text="🏆 برترین دعوت‌کنندگان:\n\n"
        for i,(u,cnt) in enumerate(sorted_inv,1): top_text+=f"{i}. {u} - {cnt} دعوت\n"
        top_text+=f"\nدعوت‌های تو: {get_invites(uid)}"
        bot.send_message(uid,top_text); return
    if "report" in t:
        if uid not in chats: bot.send_message(uid,"تو تو چت نیستی"); return
        partner=chats[uid]; reports_db[str(partner)]=reports_db.get(str(partner),0)+1
        if reports_db[str(partner)]>=2:
            banned_until[str(partner)]=time.time()+600
            try: bot.send_message(partner,f"🚫 به خاطر گزارش کاربران 10 دقیقه بن شدی")
            except: pass
        if uid in chats:
            p=chats[uid]; del chats[uid]
            if p in chats: del chats[p]
            pending_rating[str(uid)]=p
            bot.send_message(uid,"✅ گزارش ثبت شد\nبه این چت چه امتیازی میدی؟",reply_markup=rating_keyboard())
            try: bot.send_message(p,"❌ گزارش شدی و چت بسته شد",reply_markup=main_menu(p))
            except: pass
        return
    if "end" in t:
        partner=None
        if uid in chats:
            partner=chats[uid]; del chats[uid]
            if partner in chats: del chats[partner]
            pending_rating[str(uid)]=partner
            pending_rating[str(partner)]=uid
            bot.send_message(uid,"چت بسته شد ❌\nبه طرف مقابل چه امتیازی میدی؟",reply_markup=rating_keyboard())
            try: bot.send_message(partner,"چت بسته شد ❌\nبه طرف مقابل چه امتیازی میدی؟",reply_markup=rating_keyboard())
            except: pass
        global waiting
        waiting=[w for w in waiting if w["uid"]!=uid]
        if not partner:
            bot.send_message(uid,"چت بسته شد ❌",reply_markup=main_menu(uid))
    if "chat" in t or "next" in t:
        if is_banned(uid): bot.send_message(uid,f"🚫 تو بن هستی! {get_ban_time_left(uid)} باقی مونده"); return
        if uid in chats: bot.send_message(uid,"تو تو چاتی! /end بزن",reply_markup=anon_keyboard()); return
        bot.send_message(uid,"👇 دوست داری با کی وصل شی؟",reply_markup=chat_filter_keyboard())

@bot.message_handler(content_types=['voice'])
def voice_h(msg):
    uid=msg.chat.id
    lastseen[str(uid)]=time.time(); save_lastseen()
    if is_banned(uid) and not is_admin(uid):
        bot.send_message(uid,f"🚫 تو بن هستی! ⏳ {get_ban_time_left(uid)} باقی مونده")
        return
    if uid in chats:
        try: bot.send_voice(chats[uid], msg.voice.file_id)
        except: pass
        return
    bot.send_message(uid,"🎧 دارم گوش میدم...")
    try:
        f=bot.get_file(msg.voice.file_id); d=requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{f.file_path}",timeout=20).content
        vp=os.path.join(DATA_DIR,"v.ogg"); open(vp,"wb").write(d); txt=transcribe(vp)
        if txt: bot.send_message(uid,f"🗣️ گفتی: {txt}\n---\n{ask_groq(uid,txt)}")
        else: bot.send_message(uid,"نفهمیدم چی گفتی")
    except: bot.send_message(uid,"ارور ویس")

@bot.message_handler(content_types=['photo'])
def photo_h(msg):
    uid=msg.chat.id
    lastseen[str(uid)]=time.time(); save_lastseen()
    if is_banned(uid) and not is_admin(uid):
        bot.send_message(uid,f"🚫 تو بن هستی! ⏳ {get_ban_time_left(uid)} باقی مونده")
        return
    mode,_,_=get_user(uid)
    if mode=="edit_photo":
        pf=get_full(uid); pf['photo']=msg.photo[-1].file_id; full_profiles[str(uid)]=pf; save_full()
        bot.send_message(uid,"✅ عکس پروفایل ثبت شد!",reply_markup=full_profile_keyboard())
        set_user(uid,mode="chat"); return
    if uid in chats:
        try: bot.send_photo(chats[uid], msg.photo[-1].file_id, caption=msg.caption or "")
        except: pass
        return
    try:
        f=bot.get_file(msg.photo[-1].file_id); d=requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{f.file_path}",timeout=20).content
        ip=os.path.join(DATA_DIR,"in.jpg"); open(ip,"wb").write(d); im=Image.open(ip); im.thumbnail((512,512)); wp=os.path.join(DATA_DIR,"st.webp"); im.save(wp,"WEBP")
        bot.send_sticker(uid, open(wp,"rb"))
    except: pass

@bot.message_handler(content_types=['video','document','animation'])
def video_h(msg):
    uid=msg.chat.id
    lastseen[str(uid)]=time.time(); save_lastseen()
    if is_banned(uid) and not is_admin(uid):
        bot.send_message(uid,f"🚫 تو بن هستی! ⏳ {get_ban_time_left(uid)} باقی مونده")
        return
    if uid in chats: return
    mode,_,_=get_user(uid)
    if mode!="gif": return
    if get_coins(uid)<=0: bot.send_message(uid,f"💸 سکه‌ت تموم شد!\nhttps://t.me/{bot.get_me().username}?start={uid}"); return
    bot.send_message(uid,"🎞️ دارم گیف میکنم... (5 ثانیه اول)")
    try:
        file_id = msg.video.file_id if msg.video else msg.document.file_id if msg.document else msg.animation.file_id
        f=bot.get_file(file_id); data=requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{f.file_path}",timeout=40).content
        vp=os.path.join(DATA_DIR,"in_vid.mp4"); open(vp,"wb").write(data); out=video_to_gif(vp)
        if out: bot.send_animation(uid, open(out,'rb'), caption=f"✅ گیف شد\nباقی: {get_coins(uid)-1}🪙"); add_coins(uid,-1)
        else: bot.send_message(uid,"❌ ffmpeg نصب نیست")
    except Exception as e: bot.send_message(uid,f"ارور گیف: {e}")
    set_user(uid,mode="chat")

@bot.message_handler(func=lambda m: True)
def all_h(m):
    uid=m.chat.id; txt=m.text.strip(); mode,_,_=get_user(uid)
    lastseen[str(uid)]=time.time(); save_lastseen()
    if is_banned(uid) and not is_admin(uid):
        bot.send_message(uid,f"🚫 تو بن هستی!\n⏳ زمان باقی‌مانده: {get_ban_time_left(uid)}\nبعد از اتمام بن میتونی برگردی.")
        return
    if is_admin(uid):
        if mode=="admin_broadcast":
            try: all_ids = [row[0] for row in conn.execute("SELECT id FROM users").fetchall()]
            except: all_ids=[]
            all_ids = set([str(x) for x in all_ids] + list(coins_db.keys()) + list(full_profiles.keys()))
            count=0; fail=0
            bot.send_message(uid,f"⏳ ارسال به {len(all_ids)} نفر شروع شد...")
            for target in all_ids:
                try:
                    if str(target)==str(uid): continue
                    bot.send_message(int(target),f"📢 پیام مدیریت:\n\n{txt}")
                    count+=1; time.sleep(0.05)
                except: fail+=1
            bot.send_message(uid,f"✅ تموم شد\nموفق: {count}\nناموفق: {fail}",reply_markup=admin_keyboard())
            set_user(uid,mode="chat"); return
        if mode=="admin_coins":
            try:
                target_id = "".join(filter(str.isdigit, txt.strip().split()[0]))
                if len(target_id) < 5:
                    bot.send_message(uid,"❌ آیدی باید حداقل 5 رقم باشه")
                    return
                pending_coin_target[str(uid)] = target_id
                set_user(uid,mode="admin_coins_amount")
                bot.send_message(uid,f"👤 کاربر: `{target_id}`\n💰 سکه فعلی: {get_coins(target_id)}\n\nحالا مقدار سکه رو بفرست:\n`50` اضافه\n`-20` کم کردن",parse_mode="Markdown")
            except:
                bot.send_message(uid,"❌ آیدی اشتباهه")
            return
        if mode=="admin_coins_amount":
            try:
                target_id = pending_coin_target.get(str(uid))
                if not target_id:
                    bot.send_message(uid,"❌ خطا، دوباره /admin بزن")
                    set_user(uid,mode="chat"); return
                amount = int(txt.strip())
                if abs(amount) > 10000:
                    bot.send_message(uid,"⚠️ حداکثر 10000 تا در هر بار")
                    return
                current = get_coins(target_id)
                new_total = current + amount
                if new_total < 0: new_total = 0
                coins_db[str(target_id)] = new_total; save_coins()
                if str(uid) in pending_coin_target: del pending_coin_target[str(uid)]
                bot.send_message(uid,f"✅ انجام شد\n👤 {target_id}\nقبل: {current}\nتغییر: {amount:+}\nالان: {new_total}",reply_markup=admin_keyboard())
                try:
                    if amount>0: bot.send_message(int(target_id),f"💰 {amount} سکه از طرف مدیریت گرفتی!\nسکه‌هات: {new_total}")
                    else: bot.send_message(int(target_id),f"⚠️ {abs(amount)} سکه ازت کم شد\nسکه‌هات: {new_total}")
                except: pass
                set_user(uid,mode="chat")
            except:
                bot.send_message(uid,"❌ فقط عدد بفرست مثل 50 یا -20")
            return
        if mode=="admin_ban":
            try:
                parts=txt.split(); target=parts[0]
                if len(parts)==1:
                    banned_until[target]=time.time()+3600
                    bot.send_message(uid,f"🚫 {target} 1 ساعت بن شد",reply_markup=admin_keyboard())
                    try: bot.send_message(int(target),f"🚫 تو توسط مدیریت 1 ساعت بن شدی!\n⏳ زمان: 1 ساعت\nدلیل: تخلف از قوانین")
                    except: pass
                else:
                    mins=int(parts[1])
                    if mins==0:
                        if target in banned_until: del banned_until[target]
                        bot.send_message(uid,f"✅ {target} آنبن شد",reply_markup=admin_keyboard())
                        try: bot.send_message(int(target),f"✅ تو توسط مدیریت آنبن شدی! الان میتونی از ربات استفاده کنی.")
                        except: pass
                    else:
                        banned_until[target]=time.time()+mins*60
                        bot.send_message(uid,f"🚫 {target} {mins} دقیقه بن شد",reply_markup=admin_keyboard())
                        try: bot.send_message(int(target),f"🚫 تو توسط مدیریت {mins} دقیقه بن شدی!\n⏳ زمان باقی‌مانده: {mins} دقیقه\nبعد از اتمام میتونی برگردی.")
                        except: pass
            except: bot.send_message(uid,"❌ فرمت: ID یا ID دقیقه")
            set_user(uid,mode="chat"); return
        if mode=="admin_gift_make":
            try:
                parts=txt.upper().split(); code=parts[0]; coins=int(parts[1]); maxuse=int(parts[2]) if len(parts)>2 else 100
                gift_db[code]={"coins":coins,"max_uses":maxuse,"used_by":[]}; save_gift()
                bot.send_message(uid,f"✅ کد ساخته شد:\n`{code}` = {coins}🪙 {maxuse} بار",parse_mode="Markdown",reply_markup=admin_keyboard())
            except: bot.send_message(uid,"❌ فرمت: CODE COINS USES")
            set_user(uid,mode="chat"); return
        if mode=="admin_gift_del":
            c=txt.upper().strip()
            if c in gift_db: del gift_db[c]; save_gift(); bot.send_message(uid,f"✅ کد {c} حذف شد",reply_markup=admin_keyboard())
            else: bot.send_message(uid,"❌ کد پیدا نشد")
            set_user(uid,mode="chat"); return
        if mode=="admin_userinfo":
            try:
                target=txt.strip(); pf=get_full(target); coins=get_coins(target); inv=get_invites(target)
                is_b = "بله" if is_banned(target) else "خیر"
                left = f" ({get_ban_time_left(target)} باقی)" if is_banned(target) else ""
                txt2=f"👤 اطلاعات {target}:\n\n📝 اسم: {pf['name']}\n💍 وضعیت: {pf.get('relationship','❓')}\n💰 سکه: {coins}\n👥 دعوت: {inv}\n👦 جنسیت: {pf['gender']}\n🎂 سن: {pf['age']}\n🗺️ {pf['province']}-{pf['city']}\n📝 {pf['bio']}\n⭐ امتیاز: {pf['score']}\n💎 VIP: {'بله '+vip_left(target) if is_vip(target) else 'خیر'}\n🚫 بن: {is_b}{left}"
                bot.send_message(uid,txt2,reply_markup=admin_keyboard())
            except: bot.send_message(uid,"کاربر پیدا نشد")
            set_user(uid,mode="chat"); return

    if mode=="gift_redeem":
        tries = gift_tries.get(str(uid),0)
        code=txt.upper().strip()
        if code not in gift_db:
            tries+=1
            gift_tries[str(uid)]=tries
            if tries>=2:
                gift_tries[str(uid)]=0
                set_user(uid,mode="chat")
                bot.send_message(uid,"❌ دو بار کد اشتباه زدی!\nبرای تلاش مجدد دوباره روی گزینه 🎁 کد هدیه بزنید.",reply_markup=main_menu(uid))
                return
            else:
                bot.send_message(uid,f"❌ کد اشتباهه یا منقضی شده (تلاش {tries}/2)\nدوباره بفرست:")
                return
        info=gift_db[code]
        if str(uid) in info.get("used_by",[]):
            bot.send_message(uid,"⚠️ قبلا از این کد استفاده کردی!")
            set_user(uid,mode="chat")
            gift_tries[str(uid)]=0
            return
        if len(info.get("used_by",[]))>=info['max_uses']:
            bot.send_message(uid,"❌ ظرفیت این کد تموم شده")
            set_user(uid,mode="chat")
            gift_tries[str(uid)]=0
            return
        add_coins(uid,info['coins']); info.setdefault("used_by",[]).append(str(uid)); save_gift()
        gift_tries[str(uid)]=0
        bot.send_message(uid,f"🎉 {info['coins']} سکه گرفتی!\n💰 سکه‌هات: {get_coins(uid)}",reply_markup=main_menu(uid))
        set_user(uid,mode="chat"); return

    if mode=="edit_name":
        if is_link_spam(txt):
            banned_until[str(uid)]=time.time()+3600
            bot.send_message(uid,f"🚫 به خاطر گذاشتن لینک تو اسم 1 ساعت بن شدی!\n⏳ زمان: 1 ساعت")
            set_user(uid,mode="chat"); return
        if len(txt) < 2 or len(txt) > 20: bot.send_message(uid,"اسم باید بین 2 تا 20 حرف باشه:"); return
        pf=get_full(uid); pf['name']=txt[:20]; full_profiles[str(uid)]=pf; save_full()
        bot.send_message(uid,f"✅ اسم ثبت شد: {txt}",reply_markup=full_profile_keyboard()); set_user(uid,mode="chat"); return
    if mode=="edit_age":
        if not txt.isdigit() or not 10 <= int(txt) <= 70: bot.send_message(uid,"سن باید عدد بین 10 تا 70 باشه:"); return
        pf=get_full(uid); pf['age']=txt; full_profiles[str(uid)]=pf; save_full()
        bot.send_message(uid,f"✅ سن ثبت شد: {txt}",reply_markup=full_profile_keyboard()); set_user(uid,mode="chat"); return
    if mode=="edit_province":
        if is_link_spam(txt):
            banned_until[str(uid)]=time.time()+3600
            bot.send_message(uid,f"🚫 به خاطر لینک 1 ساعت بن شدی!"); set_user(uid,mode="chat"); return
        pf=get_full(uid); pf['province']=txt[:20]; full_profiles[str(uid)]=pf; save_full()
        bot.send_message(uid,f"✅ استان: {txt}\nحالا شهرت؟"); set_user(uid,mode="edit_city"); return
    if mode=="edit_city":
        if is_link_spam(txt):
            banned_until[str(uid)]=time.time()+3600
            bot.send_message(uid,f"🚫 به خاطر لینک 1 ساعت بن شدی!"); set_user(uid,mode="chat"); return
        pf=get_full(uid); pf['city']=txt[:20]; full_profiles[str(uid)]=pf; save_full()
        bot.send_message(uid,f"✅ شهر: {txt}",reply_markup=full_profile_keyboard()); set_user(uid,mode="chat"); return
    if mode=="edit_bio":
        if is_link_spam(txt):
            banned_until[str(uid)]=time.time()+3600
            bot.send_message(uid,f"🚫 به خاطر گذاشتن لینک تو بیو 1 ساعت بن شدی!\n⏳ زمان: 1 ساعت\nلینک و آیدی گذاشتن ممنوعه!")
            set_user(uid,mode="chat"); return
        pf=get_full(uid); pf['bio']=txt[:100]; full_profiles[str(uid)]=pf; save_full()
        bot.send_message(uid,f"✅ بیو ثبت شد",reply_markup=full_profile_keyboard()); set_user(uid,mode="chat"); return
    if mode=="chat_waiting_ai":
        if any(w["uid"]==uid for w in waiting):
            bot.send_chat_action(uid,'typing')
            ans=ask_groq(uid,txt,"تو کامو هستی، کاربر تو صف چت ناشناسه و حوصله‌ش سر رفته. باهاش بامزه و صمیمی فارسی حرف بزن، بگو دارم برات پارتنر پیدا میکنم. کوتاه جواب بده")
            bot.send_message(uid,f"🤖 کامو: {ans}\n\n⏳ هنوز تو صفی... /end برای لغو")
            return
        else:
            set_user(uid,mode="chat")
    if uid in chats:
        if txt.startswith("/"): return
        if is_link_spam(txt):
            spam_warnings[str(uid)]=spam_warnings.get(str(uid),0)+1
            if spam_warnings[str(uid)]>=2:
                banned_until[str(uid)]=time.time()+3600
                bot.send_message(uid,f"🚫 به خاطر ارسال لینک 1 ساعت بن شدی\n⏳ زمان: 1 ساعت")
                partner=chats.get(uid)
                if partner:
                    try: bot.send_message(partner,"🚫 طرف به خاطر اسپم بن شد. چت بسته شد.",reply_markup=main_menu(partner))
                    except: pass
                    if uid in chats: del chats[uid]
                    if partner in chats: del chats[partner]
                return
            else: bot.send_message(uid,"⚠️ ارسال لینک در چت ناشناس ممنوعه! اخطار 1/2"); return
        try: bot.send_message(chats[uid],f"💬 {txt}")
        except: pass
        return
    if mode in ["image","download","card","profile","gif"] and get_coins(uid)<=0:
        bot.send_message(uid,f"💸 سکه‌ت تموم شد!\nلینک دعوتت:\nhttps://t.me/{bot.get_me().username}?start={uid}\nهر دعوت +10 سکه"); return
    if mode=="translate": bot.send_chat_action(uid,'typing'); ans=ask_groq(uid,f"متن زیر را ترجمه کن:\nاگر انگلیسی است به فارسی روان ترجمه کن، اگر فارسی است به انگلیسی روان ترجمه کن. فقط خود ترجمه را بده:\n\n{txt}","تو مترجم حرفه‌ای هستی فقط ترجمه میدی"); bot.send_message(uid,f"🌐 ترجمه:\n{ans}"); set_user(uid,mode="chat"); return
    if mode=="weather": bot.send_chat_action(uid,'typing'); bot.send_message(uid,get_weather(txt)); set_user(uid,mode="chat"); return
    if mode=="image":
        bot.send_chat_action(uid,'upload_photo'); url=f"https://image.pollinations.ai/prompt/{requests.utils.quote(txt)}?width=1024&height=1024&nologo=true&seed={int(time.time())}"
        bot.send_photo(uid,url,caption=txt[:200]); add_coins(uid,-1); bot.send_message(uid,f"✅ باقی: {get_coins(uid)}🪙",reply_markup=main_menu(uid)); set_user(uid,mode="chat"); return
    if mode=="card": bot.send_chat_action(uid,'upload_photo'); p=make_card(txt); bot.send_photo(uid,open(p,'rb'),caption=f"🎨 {txt}\nباقی: {get_coins(uid)-1}🪙"); add_coins(uid,-1); set_user(uid,mode="chat"); return
    if mode=="profile": bot.send_chat_action(uid,'upload_photo'); p=make_profile(txt); bot.send_photo(uid,open(p,'rb'),caption=f"👑 پروفایل {txt}\nباقی: {get_coins(uid)-1}🪙"); add_coins(uid,-1); set_user(uid,mode="chat"); return
    if mode=="download" or any(x in txt.lower() for x in ["instagram.com","youtu.be","youtube.com","tiktok.com"]):
        bot.send_message(uid,"📥 دارم دانلود میکنم..."); bot.send_chat_action(uid,'upload_video')
        try:
            for f in glob.glob(os.path.join(DATA_DIR,"dl.*")):
                try: os.remove(f)
                except: pass
            import yt_dlp; opts={'format':'best[ext=mp4][height<=720]/best','outtmpl':os.path.join(DATA_DIR,'dl.%(ext)s'),'noplaylist':True,'quiet':True}
            with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([txt])
            fl=glob.glob(os.path.join(DATA_DIR,"dl.*"))
            if fl:
                with open(fl[0],'rb') as f:
                    if fl[0].endswith(".mp4"): bot.send_video(uid,f,caption="✅ دانلود شد")
                    else: bot.send_document(uid,f)
                add_coins(uid,-1); bot.send_message(uid,f"باقی: {get_coins(uid)}🪙")
            else: bot.send_message(uid,"❌ دانلود نشد")
        except: bot.send_message(uid,"❌ لینک عمومی نیست یا خرابه")
        set_user(uid,mode="chat"); return
    if mode=="summarize" and txt.startswith("http"):
        bot.send_message(uid,"🔗 دارم میخونم..."); bot.send_chat_action(uid,'typing')
        try:
            from bs4 import BeautifulSoup; html=requests.get(txt,timeout=12,headers={"User-Agent":"Mozilla/5.0"}).text; soup=BeautifulSoup(html,'html.parser')
            for tag in soup(["script","style","nav","footer","header"]): tag.decompose()
            text=soup.get_text()[:5000]; bot.send_message(uid,ask_groq(uid,f"این مقاله رو 3 نکته فارسی خلاصه کن:\n{text}","خلاصه‌کن حرفه‌ای"))
        except: bot.send_message(uid,"نتونستم بخونم")
        set_user(uid,mode="chat"); return
    if mode=="qr": import qrcode; qp=os.path.join(DATA_DIR,"qr.png"); qrcode.make(txt).save(qp); bot.send_photo(uid,open(qp,"rb"),caption="✅ QR ساخته شد"); set_user(uid,mode="chat"); return
    if mode=="voice":
        try:
            vp=os.path.join(DATA_DIR,"v.mp3")
            try: gTTS(txt,lang='fa').save(vp)
            except: gTTS(txt,lang='en').save(vp)
            bot.send_voice(uid,open(vp,"rb"))
        except: pass
        set_user(uid,mode="chat"); return
    if mode=="caption": bot.send_chat_action(uid,'typing'); bot.send_message(uid,ask_groq(uid,f"3 کپشن اینستا جذاب برای {txt} با هشتگ بساز")); set_user(uid,mode="chat"); return
    bot.send_chat_action(uid,'typing'); bot.send_message(uid,ask_groq(uid,txt))

# یادآوری هوشمند هر 1 ساعت چک میکنه
def reminder_loop():
    while True:
        try:
            time.sleep(3600)
            now=time.time()
            for uid_str, last in list(lastseen.items()):
                if now - last > 24*3600 and now - last < 25*3600: # بین 24 تا 25 ساعت
                    try:
                        bot.send_message(int(uid_str),f"👋 دلم برات تنگ شده! 😢\n\n🎡 گردونت آماده‌ست، یه نفر هم تو چت ناشناس منتظرته!\nبزن /start برگرد 💖",reply_markup=main_menu(int(uid_str)))
                        lastseen[uid_str]=now; save_lastseen()
                        time.sleep(1)
                    except: pass
        except: pass

threading.Thread(target=reminder_loop, daemon=True).start()

print(f"✅ KAMO V8.4.0 LIVE - WHEEL+VIP+ANTISPAM+REMINDER")
bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
