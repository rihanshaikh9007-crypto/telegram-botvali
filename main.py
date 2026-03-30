import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import sqlite3
import random
import string
import os
import time
from datetime import datetime
from flask import Flask
import threading

# Yahan apna bot token dalein
TOKEN = '8579040508:AAGBJ4gIPtLiqj1fb88zCVGdIWDT48i_FVQ'
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# Aapki Admin ID aur Approval Channel
ADMIN_ID = 1484173564
APPROVAL_CHANNEL = "@ValiModes_key" # Yahan approval requests aayengi

# ================= DATABASE SETUP =================
conn = sqlite3.connect('webseries_bot.db', check_same_thread=False)
c = conn.cursor()

# Channels table create karna
c.execute('''CREATE TABLE IF NOT EXISTS channels (channel_id TEXT, link TEXT)''')

# 🎨 Naya 'style' column safe tareeke se add karna (for Real Colors)
try:
    c.execute("ALTER TABLE channels ADD COLUMN style TEXT DEFAULT 'primary'")
    conn.commit()
except:
    pass 

c.execute('''CREATE TABLE IF NOT EXISTS join_reqs (user_id INTEGER, channel_id TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, join_date TEXT, coins INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0)''')
c.execute('''CREATE TABLE IF NOT EXISTS pending_refs (user_id INTEGER PRIMARY KEY, referrer_id INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS completed_refs (user_id INTEGER PRIMARY KEY, referrer_id INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS vip_keys (key_code TEXT PRIMARY KEY, duration INTEGER, status TEXT DEFAULT 'UNUSED', used_by INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT)''')
c.execute("INSERT OR IGNORE INTO settings (name, value) VALUES ('key_link', 'https://www.mediafire.com/file/if3uvvwjbj87lo2/DRIPCLIENT_v6.2_GLOBAL_AP.apks/file')")
conn.commit()

# ================= SECURITY / ANTI-SPAM =================
user_last_msg = {}
temp_channel_data = {} # Channel add karte waqt data hold karne ke liye

def flood_check(user_id):
    now = time.time()
    if user_id in user_last_msg and now - user_last_msg[user_id] < 1.0:
        return True
    user_last_msg[user_id] = now
    return False

def is_user_banned(user_id):
    c.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    return res and res[0] == 1

# ================= FLASK WEB SERVER =================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running perfectly on Render with Colored Buttons!"
def run_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


# ================= 💰 ADMIN ADD COINS =================
@bot.message_handler(commands=['addcoins'])
def add_coins(message):
    if message.chat.id != ADMIN_ID: return
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ Format: <code>/addcoins USER_ID COINS</code>")
            return
        target_user = int(parts[1])
        amount = int(parts[2])
        
        c.execute("SELECT * FROM users WHERE user_id=?", (target_user,))
        if not c.fetchone():
            bot.reply_to(message, "❌ User not found in database.")
            return
            
        c.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, target_user))
        conn.commit()
        bot.reply_to(message, f"✅ <b>{amount} Coins</b> added to {target_user}.")
        try: bot.send_message(target_user, f"🎁 Admin ne aapko <b>{amount} Coins</b> bheje hain!")
        except: pass
    except ValueError:
        bot.reply_to(message, "❌ Numbers only!")


# ================= 🔗 LINK CHANGER =================
@bot.message_handler(commands=['change'])
def change_link(message):
    if message.chat.id != ADMIN_ID: return
    try:
        new_link = message.text.replace('/change', '').strip()
        if new_link == "":
            bot.reply_to(message, "❌ Link cannot be empty!")
            return
        c.execute("UPDATE settings SET value=? WHERE name='key_link'", (new_link,))
        conn.commit()
        bot.reply_to(message, f"✅ <b>Link Updated!</b>\nNew link for keys:\n{new_link}")
    except Exception:
        bot.reply_to(message, "❌ Format: <code>/change [LINK]</code>")


# ================= ADMIN PANEL =================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id != ADMIN_ID: return 
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("➕ Add Channel", callback_data="add_channel"),
               InlineKeyboardButton("➖ Remove Channel", callback_data="remove_channel"))
    markup.add(InlineKeyboardButton("📋 View Added Channels", callback_data="view_channels"))
    markup.add(InlineKeyboardButton("📊 Stats & Users", callback_data="adm_stats"),
               InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"))
    markup.add(InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"),
               InlineKeyboardButton("✅ Unban User", callback_data="adm_unban"))
    markup.add(InlineKeyboardButton("🔑 Gen 1-Day VIP", callback_data="adm_key1"),
               InlineKeyboardButton("🔑 Gen 7-Day VIP", callback_data="adm_key7"))
    bot.send_message(message.chat.id, "👨‍💻 <b>Admin Panel</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["add_channel", "remove_channel", "view_channels"] or call.data.startswith("adm_") or call.data.startswith("style_"))
def admin_callbacks(call):
    if call.message.chat.id != ADMIN_ID: return

    # 🎨 REAL COLOR SELECTION HANDLER 
    if call.data.startswith("style_"):
        style = call.data.split("_")[1] # primary, success, danger, secondary
        data = temp_channel_data.get(call.message.chat.id)
        if data:
            c.execute("INSERT INTO channels (channel_id, link, style) VALUES (?, ?, ?)", (data['ch_id'], data['link'], style))
            conn.commit()
            bot.edit_message_text(f"✅ Channel <code>{data['ch_id']}</code> successfully add ho gaya!\n🎨 Button Color Saved as: {style.upper()}", chat_id=call.message.chat.id, message_id=call.message.message_id)
            del temp_channel_data[call.message.chat.id]
        return

    if call.data == "add_channel":
        msg = bot.send_message(call.message.chat.id, "🤖 Pehle bot ko channel me Admin banao!\n\nPhir Channel ID send karo:")
        bot.register_next_step_handler(msg, process_add_channel)
        
    elif call.data == "view_channels":
        try:
            c.execute("SELECT channel_id, link, style FROM channels")
        except:
            c.execute("SELECT channel_id, link FROM channels")
        channels = c.fetchall()
        if not channels:
            bot.send_message(call.message.chat.id, "❌ No channels added.")
            return
        text = "📋 <b>Added Channels:</b>\n\n"
        for ch in channels:
            style = ch[2] if len(ch) > 2 and ch[2] else 'primary'
            text += f"ID: <code>{ch[0]}</code>\n🎨 Color: {style.upper()}\nLink: {ch[1]}\n\n"
        bot.send_message(call.message.chat.id, text, disable_web_page_preview=True)
        
    elif call.data == "remove_channel":
        msg = bot.send_message(call.message.chat.id, "🗑️ Channel ID bhejo remove karne ke liye:")
        bot.register_next_step_handler(msg, process_remove_channel)
    elif call.data == "adm_stats":
        c.execute("SELECT COUNT(*) FROM users")
        tot = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
        ban = c.fetchone()[0]
        bot.send_message(call.message.chat.id, f"📊 <b>BOT STATS</b>\n\n👥 Total Users: {tot}\n🟢 Active: {tot-ban}\n🔴 Banned: {ban}")
    elif call.data == "adm_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 Broadcast message bhejo:")
        bot.register_next_step_handler(msg, process_broadcast)
    elif call.data == "adm_ban":
        msg = bot.send_message(call.message.chat.id, "🚫 User ID to BAN:")
        bot.register_next_step_handler(msg, lambda m: toggle_ban(m, 1))
    elif call.data == "adm_unban":
        msg = bot.send_message(call.message.chat.id, "✅ User ID to UNBAN:")
        bot.register_next_step_handler(msg, lambda m: toggle_ban(m, 0))
    elif call.data in ["adm_key1", "adm_key7"]:
        days = 1 if call.data == "adm_key1" else 7
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        c.execute("INSERT INTO vip_keys (key_code, duration) VALUES (?, ?)", (code, days))
        conn.commit()
        bot.send_message(call.message.chat.id, f"✅ <b>{days}-Day VIP Key:</b>\n<code>{code}</code>")

def process_add_channel(message):
    ch_id = message.text.strip()
    try:
        bot_member = bot.get_chat_member(ch_id, bot.get_me().id)
        if bot_member.status != 'administrator':
            bot.send_message(message.chat.id, "❌ Bot is channel me Admin nahi hai!")
            return
        invite_link = bot.create_chat_invite_link(ch_id, creates_join_request=True).invite_link
        
        temp_channel_data[message.chat.id] = {'ch_id': ch_id, 'link': invite_link}
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🔵 Blue (Primary)", callback_data="style_primary"),
            InlineKeyboardButton("🟢 Green (Success)", callback_data="style_success"),
            InlineKeyboardButton("🔴 Red (Danger)", callback_data="style_danger"),
            InlineKeyboardButton("⚪ Grey (Secondary)", callback_data="style_secondary")
        )
        bot.send_message(message.chat.id, "🎨 <b>Is Channel ke Button ka Color kya rakhna hai?</b>\nNiche diye gaye real color options mein se choose karein:", reply_markup=markup)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")

def process_remove_channel(message):
    c.execute("DELETE FROM channels WHERE channel_id=?", (message.text.strip(),))
    conn.commit()
    bot.send_message(message.chat.id, "✅ Channel removed!")

def process_broadcast(message):
    bot.send_message(message.chat.id, "⏳ Broadcasting started...")
    c.execute("SELECT user_id FROM users WHERE is_banned=0")
    users = c.fetchall()
    sent, failed = 0, 0
    for u in users:
        try:
            bot.copy_message(u[0], message.chat.id, message.message_id)
            sent += 1
            time.sleep(0.05)
        except: failed += 1
    bot.send_message(message.chat.id, f"✅ <b>Broadcast Done!</b>\nSuccess: {sent} | Failed: {failed}")

def toggle_ban(message, status):
    try:
        uid = int(message.text.strip())
        c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (status, uid))
        conn.commit()
        bot.reply_to(message, f"✅ Done!")
    except: bot.reply_to(message, "❌ Invalid ID.")


# ================= JOIN REQUEST & FORCE SUB DYNAMIC SYSTEM =================
def get_unjoined_channels(user_id):
    """Ye function sirf un channels ki list nikalega jo user ne abhi tak join NAHI kiye hain."""
    try:
        c.execute("SELECT channel_id, link, style FROM channels")
    except:
        c.execute("SELECT channel_id, link, 'primary' as style FROM channels")
    
    channels = c.fetchall()
    unjoined = []
    
    for ch in channels:
        joined = False
        try:
            if bot.get_chat_member(ch[0], user_id).status in ['member', 'administrator', 'creator']: 
                joined = True
        except: 
            pass
            
        if not joined:
            c.execute("SELECT * FROM join_reqs WHERE user_id=? AND channel_id=?", (user_id, ch[0]))
            if c.fetchone(): 
                joined = True
                
        if not joined:
            unjoined.append(ch)
            
    return unjoined

def check_user_status(user_id):
    return len(get_unjoined_channels(user_id)) == 0

@bot.chat_join_request_handler()
def handle_join_request(message: telebot.types.ChatJoinRequest):
    c.execute("INSERT INTO join_reqs (user_id, channel_id) VALUES (?, ?)", (message.from_user.id, str(message.chat.id)))
    conn.commit()

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if flood_check(uid) or is_user_banned(uid): return

    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    if not c.fetchone():
        date = datetime.now().strftime("%Y-%m-%d")
        c.execute("INSERT INTO users (user_id, username, join_date) VALUES (?, ?, ?)", (uid, message.from_user.username or "Unknown", date))
        
        args = message.text.split()
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
            if ref_id != uid:
                c.execute("SELECT * FROM completed_refs WHERE user_id=?", (uid,))
                if not c.fetchone():
                    c.execute("UPDATE users SET coins = coins + 2 WHERE user_id=?", (ref_id,))
                    c.execute("INSERT INTO completed_refs (user_id, referrer_id) VALUES (?, ?)", (uid, ref_id))
                    conn.commit()
                    try: bot.send_message(ref_id, "🎉 <b>Congrats!</b>\nKisi ne aapke link se bot start kiya hai. <b>+2 Coins</b> Added!")
                    except: pass
        else:
            conn.commit()
            
    send_force_sub(message.chat.id, uid)

def send_force_sub(chat_id, user_id):
    unjoined = get_unjoined_channels(user_id)
    
    if not unjoined:
        send_main_menu(chat_id)
        return
        
    markup = InlineKeyboardMarkup()
    row = []
    
    # Sirf wahi channels dikhayega jo join nahi kiye gaye!
    for i, ch in enumerate(unjoined):
        link = ch[1]
        btn_style = ch[2] if len(ch) > 2 and ch[2] else 'primary'
        row.append(InlineKeyboardButton(f"Join Channel", url=link, style=btn_style))
        
        if len(row) == 2:
            markup.add(*row)
            row = []
    if row:
        markup.add(*row)
        
    markup.add(InlineKeyboardButton("✅ Done !!", callback_data="verify_channels", style="success"))
    
    image_url = "https://files.catbox.moe/wcfmqd.jpg" 
    caption = "𝗛ᴇʟʟᴏ 𝗨ꜱᴇʀ 👻 𝐁𝐎𝐓\n\nALL CHANNEL JOIN 🥰\n\n👻 Sab channels join karo phir Done !! dabao"
    
    bot.send_photo(chat_id, image_url, caption=caption, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "verify_channels")
def verify_callback(call):
    uid = call.from_user.id
    if is_user_banned(uid): return
    
    unjoined = get_unjoined_channels(uid)
    
    if not unjoined:
        # Saare channels join ho gaye!
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_main_menu(call.message.chat.id)
        bot.answer_callback_query(call.id, "✅ Verified successfully!", show_alert=False)
    else:
        # Kuch channels baaki hain! List update karo aur "Try Again" button dalo.
        markup = InlineKeyboardMarkup()
        row = []
        for i, ch in enumerate(unjoined):
            link = ch[1]
            btn_style = ch[2] if len(ch) > 2 and ch[2] else 'primary'
            row.append(InlineKeyboardButton(f"Join Channel", url=link, style=btn_style))
            
            if len(row) == 2:
                markup.add(*row)
                row = []
        if row:
            markup.add(*row)
            
        # 🔴 "Try Again" wala button (Red color me aayega)
        markup.add(InlineKeyboardButton("🔄 Try Again", callback_data="verify_channels", style="danger"))
        
        try:
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id, "❌ Aapne abhi tak sabhi channels join nahi kiye! Baki bache hue channels join karein.", show_alert=True)
        except Exception as e:
            bot.answer_callback_query(call.id, "❌ Pehle bache hue channels join karo aur fir Try Again dabao!", show_alert=True)


# ================= MAIN MENU & GET KEY LOGIC =================
def send_main_menu(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("👤 My Account"), KeyboardButton("🔗 Refer & Earn"))
    markup.add(KeyboardButton("🎁 Get Key (15 Coins)"), KeyboardButton("🔑 Use VIP Key"))
    bot.send_message(chat_id, "✅ Use the menu below to navigate:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def text_commands(message):
    uid = message.from_user.id
    if flood_check(uid) or is_user_banned(uid): return

    # 🔴🔥 SECURITY FIX: MENU BLOCKER 🔥🔴
    if not check_user_status(uid):
        hide_markup = telebot.types.ReplyKeyboardRemove()
        bot.reply_to(message, "❌ <b>Access Denied!</b>\n\nAapne abhi tak sabhi channels join nahi kiye hain. Kripya pehle niche diye gaye channels ko join karein aur <b>Done !!</b> dabayein.", reply_markup=hide_markup)
        send_force_sub(message.chat.id, uid)
        return
    # ----------------------------------------------------
    
    c.execute("SELECT coins FROM users WHERE user_id=?", (uid,))
    res = c.fetchone()
    if not res: return
    coins = res[0]
    text = message.text

    if text == "👤 My Account":
        bot.send_message(uid, f"👤 <b>Account Stats</b>\n\n🆔 User ID: <code>{uid}</code>\n💰 Coins: <b>{coins}</b>")
        
    elif text == "🔗 Refer & Earn":
        bot_usr = bot.get_me().username
        bot.send_message(uid, f"📢 <b>REFER & EARN</b>\n\nInvite friends & get <b>2 Coins</b> per join!\n\n🔗 Your Link:\nhttps://t.me/{bot_usr}?start={uid}")
        
    elif text == "🎁 Get Key (15 Coins)":
        if coins >= 15:
            c.execute("UPDATE users SET coins = coins - 15 WHERE user_id=?", (uid,))
            conn.commit()
            
            req_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            username = message.from_user.username
            user_mention = f"@{username}" if username else f"User ID: {uid}"

            req_text = (
                f"🆕 <b>New Key Request</b>\n\n"
                f"👤 <b>User:</b> {user_mention}\n"
                f"🆔 <b>ID:</b> <code>{uid}</code>\n"
                f"⏰ <b>Time:</b> {req_time}"
            )

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✅ APPROVAL", callback_data=f"approve_{uid}"),
                InlineKeyboardButton("❌ REJECTED", callback_data=f"reject_{uid}")
            )

            try:
                bot.send_message(APPROVAL_CHANNEL, req_text, reply_markup=markup)
                
                success_msg = (
                    "⏳ <b>Request Successfully Sent!</b>\n\n"
                    "Aapki VIP Key ki request Admin ko bhej di gayi hai. Approval milte hi aapko yahin bot me key mil jayegi.\n\n"
                    "⚠️ <b>IMPORTANT WARNING:</b>\n"
                    "Agar aapne <b>@ValiModes_key</b> channel join nahi kiya hai, toh Admin aapki request ko <b>REJECT</b> kar dega aur aapko key nahi milegi!\n\n"
                    "👉 Abhi check karein: @ValiModes_key"
                )
                bot.send_message(uid, success_msg)
                
            except Exception as e:
                c.execute("UPDATE users SET coins = coins + 15 WHERE user_id=?", (uid,))
                conn.commit()
                bot.send_message(uid, f"❌ Error: Admin ne abhi tak bot ko {APPROVAL_CHANNEL} me admin nahi banaya hai. (Coins refunded)")

        else:
            bot.send_message(uid, f"❌ <b>Coins Kam Hain!</b>\n\nKey lene ke liye <b>15 Coins</b> chahiye.\nAapke paas abhi sirf <b>{coins} Coins</b> hain. Doston ko refer karo!")

    elif text == "🔑 Use VIP Key":
        msg = bot.send_message(uid, "Send your generated VIP Key here:")
        bot.register_next_step_handler(msg, process_vip_key)

def process_vip_key(message):
    key = message.text.strip()
    uid = message.from_user.id
    c.execute("SELECT duration FROM vip_keys WHERE key_code=? AND status='UNUSED'", (key,))
    res = c.fetchone()
    if res:
        c.execute("UPDATE vip_keys SET status='USED', used_by=? WHERE key_code=?", (uid, key))
        conn.commit()
        bot.send_message(uid, f"✅ <b>VIP Key Activated!</b>\nYou now have VIP Access for {res[0]} days.")
    else:
        bot.send_message(uid, "❌ <b>Invalid or Used Key!</b>")


# ================= APPROVE / REJECT LOGIC =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_approval(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "YE TERE MAI KAM NAHI KAREGA LADLE TO ABHI BACHA HAI", show_alert=True)
        return

    action, uid_str = call.data.split("_")
    uid = int(uid_str)

    if action == "approve":
        try:
            bot.edit_message_text(f"{call.message.text}\n\n✅ <b>STATUS: APPROVED</b>", chat_id=call.message.chat.id, message_id=call.message.message_id)
        except:
            pass
        send_dynamic_key(uid)

    elif action == "reject":
        try:
            bot.edit_message_text(f"{call.message.text}\n\n❌ <b>STATUS: REJECTED</b>", chat_id=call.message.chat.id, message_id=call.message.message_id)
        except:
            pass
            
        c.execute("UPDATE users SET coins = coins + 15 WHERE user_id=?", (uid,))
        conn.commit()
        
        try:
            bot.send_message(uid, "❌ <b>Request Rejected!</b>\nAdmin ne aapki request reject kar di hai kyunki aapne sab channels join nahi kiye (@ValiModes_key). Aapke 15 coins wapas aa gaye hain.")
        except:
            pass


# ================= DYNAMIC KEY GENERATOR =================
def send_dynamic_key(chat_id):
    key = f"{random.randint(1000000000, 9999999999)}"
    
    c.execute("SELECT value FROM settings WHERE name='key_link'")
    dynamic_link = c.fetchone()[0]
    
    text = (
        f"Key - <code>{key}</code>\n\n"
        f"<a href='https://t.me/+MkNcxGuk-w43MzBl'>DRIP SCINET APK - {dynamic_link}</a>"
    )
    
    try:
        bot.send_message(chat_id, "🎉 <b>Congratulations!</b>\nAapki request Admin ne Approve kar di hai. Ye rahi aapki key 👇")
        bot.send_message(chat_id, text, disable_web_page_preview=True)
    except Exception as e:
        print(f"Error sending key to {chat_id}: {e}")

# ================= START SYSTEM =================
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    print("Bot is running...")
    bot.infinity_polling(allowed_updates=telebot.util.update_types)
