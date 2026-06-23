import telebot
from telebot.types import (InlineKeyboardMarkup, InlineKeyboardButton,
                            ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto,
                            LabeledPrice)
import sqlite3, random, time, io, os, json, math, requests, logging
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

TOKEN = os.environ.get('BOT_TOKEN', '8558967164:AAFQS-bf5V3cbsuF-78RJqCyLjSCQlv6FtI')
bot   = telebot.TeleBot(TOKEN)

PREMIUM_PRICE_STARS = 25
PREMIUM_DAYS = 30
PREMIUM_OWNER = "@kayum_xll"

# ============================================================
# ADMIN ID LAR (O'ZINGIZNIKINI QO'SHING)
# ============================================================
ADMIN_IDS = [8321761894, 6473909680]  # Admin ID lar

conn = sqlite3.connect('mbtiuzbot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.executescript('''
CREATE TABLE IF NOT EXISTS users (
    user_id          INTEGER PRIMARY KEY,
    nickname         TEXT UNIQUE,
    mbti_type        TEXT,
    mbti_answers     TEXT,
    profile_open     INTEGER DEFAULT 1,
    is_premium       INTEGER DEFAULT 0,
    premium_until    TEXT,
    created_at       TEXT
);
CREATE TABLE IF NOT EXISTS relationships (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id     INTEGER,
    to_id       INTEGER,
    rel_type    TEXT,
    status      TEXT DEFAULT 'pending',
    created_at   TEXT
);
CREATE TABLE IF NOT EXISTS tests (
    test_id      TEXT PRIMARY KEY,
    creator_id   INTEGER,
    creator_name TEXT,
    creator_photo TEXT,
    answers      TEXT,
    created_at   TEXT
);
CREATE TABLE IF NOT EXISTS participants (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id          TEXT,
    participant_id   INTEGER,
    participant_name TEXT,
    answers          TEXT,
    similarity       INTEGER,
    created_at       TEXT
);
CREATE TABLE IF NOT EXISTS user_photos (
    user_id       INTEGER PRIMARY KEY,
    photo_file_id TEXT
);
''')
conn.commit()

_FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
def lf(size, bold=False):
    try:    return ImageFont.truetype(_FB if bold else _FR, size)
    except: return ImageFont.load_default()

def _tcx(draw, txt, cx, y, font, fill):
    bb = draw.textbbox((0,0), txt, font=font)
    draw.text((cx-(bb[2]-bb[0])//2, y), txt, fill=fill, font=font)

def _heart(draw, cx, cy, s, fill):
    draw.ellipse([cx-s,cy-s,cx,cy], fill=fill)
    draw.ellipse([cx,cy-s,cx+s,cy], fill=fill)
    draw.polygon([(cx-s,cy),(cx+s,cy),(cx,cy+int(s*1.4))], fill=fill)

COMPAT_QUESTIONS = [
    {"text": "Sizning tug'ilgan kuningiz qaysi faslda?", "ask_friend": "Sizning tug'ilgan kuningiz qaysi faslda?",
     "options": ["🌸 Bahorda", "🌞 Yozda", "🍂 Kuzda", "❄️ Qishda"],
     "image": "https://images.pexels.com/photos/290595/pexels-photo-290595.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi qo'lingizni ko'proq ishlatasiz?", "ask_friend": "Siz qaysi qo'lingizni ko'proq ishlatasiz?",
     "options": ["🤚 O'ng qo'l", "🤙 Chap qo'l"],
     "image": "https://images.pexels.com/photos/104961/pexels-photo-104961.jpeg?auto=compress&w=1200"},
    {"text": "Siz o'zingizni uyatchan deb hisoblaysizmi?", "ask_friend": "Siz o'zingizni uyatchan deb hisoblaysizmi?",
     "options": ["✅ Ha", "❌ Yo'q"],
     "image": "https://images.pexels.com/photos/221183/pexels-photo-221183.jpeg?auto=compress&w=1200"},
    {"text": "Sizning zodiac belgingiz nima?", "ask_friend": "Sizning zodiac belgingiz nima?",
     "options": ["♈ Qo'y", "♉ Buqa", "♊ Egizaklar", "♋ Qisqichbaqa", "♌ Sher", "♍ Bokira",
                "♎ Tarozi", "♏ Chayon", "♐ Sagittarius", "♑ Tog' echkisi", "♒ Kova", "♓ Baliqlar", "🚫 Ishonmayman"],
     "image": "https://images.pexels.com/photos/1122475/pexels-photo-1122475.jpeg?auto=compress&w=1200"},
    {"text": "Sizning ko'zlaringizning rangi qanday?", "ask_friend": "Sizning ko'zlaringizning rangi qanday?",
     "options": ["💚 Yashil", "💙 Ko'k", "🤎 Jigarrang", "🧡 Amber", "⚫ Qora"],
     "image": "https://images.pexels.com/photos/33465/eye-eyelash-eyelashes-facial.jpg?auto=compress&w=1200"},
    {"text": "Siz shirinliklarni yoqtirasizmi?", "ask_friend": "Siz shirinliklarni yoqtirasizmi?",
     "options": ["🍰 Ha, juda", "❌ Yo'q, unchalik emas"],
     "image": "https://images.pexels.com/photos/291528/pexels-photo-291528.jpeg?auto=compress&w=1200"},
    {"text": "Sizning eng sevimli ichimligingiz qaysi?", "ask_friend": "Sizning eng sevimli ichimligingiz qaysi?",
     "options": ["🍵 Choy", "☕ Qahva", "🧃 Sharbat", "🥛 Sut", "🥤 Ko'pikli choy", "💧 Suv", "🍋 Limonad", "⚡ Energetik", "🍺 Alkogol"],
     "image": "https://images.pexels.com/photos/1405765/pexels-photo-1405765.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi telefon turidan foydalanasiz?", "ask_friend": "Siz qaysi telefon turidan foydalanasiz?",
     "options": ["🤖 Android", "🍎 iPhone"],
     "image": "https://images.pexels.com/photos/607812/pexels-photo-607812.jpeg?auto=compress&w=1200"},
    {"text": "Siz bo'sh vaqtingizda nima qilishni yaxshi ko'rasiz?", "ask_friend": "Siz bo'sh vaqtingizda nima qilishni yaxshi ko'rasiz?",
     "options": ["🎨 Chizish", "🎵 Musiqa", "💃 Raqs", "🎤 Rap", "🎮 O'yinlar", "⚽ Sport",
                "🍳 Pishirish", "🖼 San'at", "📝 Blog", "📚 O'qish", "✈️ Sayohat", "📺 Seriallar"],
     "image": "https://images.pexels.com/photos/2622116/pexels-photo-2622116.jpeg?auto=compress&w=1200"},
    {"text": "Siz hozirda qayerda o'qiysiz/ishlaysiz?", "ask_friend": "Siz hozirda qayerda o'qiysiz/ishlaysiz?",
     "options": ["🏫 Maktabda", "🏛 Kollejda", "🎓 Universitetda", "💼 Ishda", "🔍 Qidirvapman"],
     "image": "https://images.pexels.com/photos/998641/pexels-photo-998641.jpeg?auto=compress&w=1200"},
    {"text": "Siz tong odammisiz yoki kechki odammisiz?", "ask_friend": "Siz tong odammisiz yoki kechki odammisiz?",
     "options": ["🌅 Tong", "🌙 Kech"],
     "image": "https://images.pexels.com/photos/66997/pexels-photo-66997.jpeg?auto=compress&w=1200"},
    {"text": "Siz kitob o'qishni yoki film ko'rishni afzal ko'rasiz?", "ask_friend": "Siz kitob o'qishni yoki film ko'rishni afzal ko'rasiz?",
     "options": ["📚 Kitob", "🎬 Film"],
     "image": "https://images.pexels.com/photos/261876/pexels-photo-261876.jpeg?auto=compress&w=1200"},
    {"text": "Siz dengiz yoki tog'ni afzal ko'rasiz?", "ask_friend": "Siz dengiz yoki tog'ni afzal ko'rasiz?",
     "options": ["🌊 Dengiz", "⛰️ Tog'"],
     "image": "https://images.pexels.com/photos/1903702/pexels-photo-1903702.jpeg?auto=compress&w=1200"},
    {"text": "Siz qanday muhitda bo'lishni yaxshi ko'rasiz?", "ask_friend": "Siz qanday muhitda bo'lishni yaxshi ko'rasiz?",
     "options": ["🎉 Shovqinli, jonli", "🌿 Tinch, sokin"],
     "image": "https://images.pexels.com/photos/3228652/pexels-photo-3228652.jpeg?auto=compress&w=1200"},
    {"text": "Siz ertalab nima ichishni afzal ko'rasiz?", "ask_friend": "Siz ertalab nima ichishni afzal ko'rasiz?",
     "options": ["☕ Kofe", "🍵 Choy"],
     "image": "https://images.pexels.com/photos/302899/pexels-photo-302899.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi faslni ko'proq yoqtirasiz?", "ask_friend": "Siz qaysi faslni ko'proq yoqtirasiz?",
     "options": ["☀️ Yoz", "❄️ Qish"],
     "image": "https://images.pexels.com/photos/105152/pexels-photo-105152.jpeg?auto=compress&w=1200"},
    {"text": "Siz kunning qaysi vaqtini yaxshi ko'rasiz?", "ask_friend": "Siz kunning qaysi vaqtini yaxshi ko'rasiz?",
     "options": ["🌄 Tong", "🌞 Kuni", "🌅 Kech", "🌙 Tun"],
     "image": "https://images.pexels.com/photos/270182/pexels-photo-270182.jpeg?auto=compress&w=1200"},
    {"text": "Siz uy hayvonlarini yoqtirasizmi?", "ask_friend": "Siz uy hayvonlarini yoqtirasizmi?",
     "options": ["🐕 Ha", "🐈 Faqat mushuk", "🐶 Faqat it", "❌ Yo'q"],
     "image": "https://images.pexels.com/photos/257540/pexels-photo-257540.jpeg?auto=compress&w=1200"},
    {"text": "Siz qayerda yashashni afzal ko'rasiz?", "ask_friend": "Siz qayerda yashashni afzal ko'rasiz?",
     "options": ["🏙️ Shahar", "🌾 Qishloq", "🏖️ Dengiz bo'yi"],
     "image": "https://images.pexels.com/photos/208745/pexels-photo-208745.jpeg?auto=compress&w=1200"},
    {"text": "Siz ko'proq nima bilan shug'ullanishni yoqtirasiz?", "ask_friend": "Siz ko'proq nima bilan shug'ullanishni yoqtirasiz?",
     "options": ["⚽ Sport", "🎨 San'at", "🎵 Musiqa", "📚 O'qish"],
     "image": "https://images.pexels.com/photos/3754287/pexels-photo-3754287.jpeg?auto=compress&w=1200"},
    {"text": "Siz dam olish kunida nima qilishni afzal ko'rasiz?", "ask_friend": "Siz dam olish kunida nima qilishni afzal ko'rasiz?",
     "options": ["👥 Do'stlar bilan", "🏠 Uyda yolg'iz", "👪 Oilam bilan"],
     "image": "https://images.pexels.com/photos/3184418/pexels-photo-3184418.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi musiqa janrini yaxshi ko'rasiz?", "ask_friend": "Siz qaysi musiqa janrini yaxshi ko'rasiz?",
     "options": ["🎸 Rock", "🎹 Pop", "🎵 Klassik", "🎤 Hip-hop", "🎧 Elektron", "🪕 Folk", "🎶 Jazz"],
     "image": "https://images.pexels.com/photos/1763075/pexels-photo-1763075.jpeg?auto=compress&w=1200"},
    {"text": "Siz qanday dam olishni afzal ko'rasiz?", "ask_friend": "Siz qanday dam olishni afzal ko'rasiz?",
     "options": ["🛌 Uxlash", "📺 TV ko'rish", "🚶 Sayr qilish", "✈️ Sayohat", "🛍️ Xarid"],
     "image": "https://images.pexels.com/photos/211526/pexels-photo-211526.jpeg?auto=compress&w=1200"},
    {"text": "Sizning hayotga qarashingiz qanday?", "ask_friend": "Sizning hayotga qarashingiz qanday?",
     "options": ["😊 Optimist", "😔 Realist", "🤔 Pessimist", "🎭 Falsafiy"],
     "image": "https://images.pexels.com/photos/260024/pexels-photo-260024.jpeg?auto=compress&w=1200"},
    {"text": "Siz yangi odamlar bilan tanishganda nima his qilasiz?", "ask_friend": "Siz yangi odamlar bilan tanishganda nima his qilasiz?",
     "options": ["😊 Hayajonliman", "😬 Biroz qo'rqaman", "😐 Befarq", "🤩 Juda xursandman"],
     "image": "https://images.pexels.com/photos/1181690/pexels-photo-1181690.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi rangni yaxshi ko'rasiz?", "ask_friend": "Siz qaysi rangni yaxshi ko'rasiz?",
     "options": ["🔵 Ko'k", "🔴 Qizil", "🟢 Yashil", "🟡 Sariq", "🟣 Binafsha", "⚫ Qora", "⚪ Oq"],
     "image": "https://images.pexels.com/photos/1148399/pexels-photo-1148399.jpeg?auto=compress&w=1200"},
    {"text": "Siz stressni qanday yengasiz?", "ask_friend": "Siz stressni qanday yengasiz?",
     "options": ["🎵 Musiqa tinglash", "🏃 Sport qilish", "😴 Uxlash", "🗣 Gaplashish", "🎮 O'yin o'ynash"],
     "image": "https://images.pexels.com/photos/3822622/pexels-photo-3822622.jpeg?auto=compress&w=1200"},
    {"text": "Siz do'stingizga sovg'a sifatida nima olasiz?", "ask_friend": "Siz do'stingizga sovg'a sifatida nima olasiz?",
     "options": ["💐 Gul", "🎂 Tort", "📚 Kitob", "🎁 Kiyim", "💰 Pul", "✈️ Sayohat"],
     "image": "https://images.pexels.com/photos/264895/pexels-photo-264895.jpeg?auto=compress&w=1200"},
    {"text": "Siz qanday inson ekansiz?", "ask_friend": "Siz qanday inson ekansiz?",
     "options": ["🤗 Ochiq va samimiy", "🧠 Aqlli va mulohazali", "😄 Kulgili va qiziqarli", "🕊 Tinch va xotirjam"],
     "image": "https://images.pexels.com/photos/1056553/pexels-photo-1056553.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi turdagi filmlarni yaxshi ko'rasiz?", "ask_friend": "Siz qaysi turdagi filmlarni yaxshi ko'rasiz?",
     "options": ["😂 Komediya", "😱 Qo'rqinchli", "❤️ Romantik", "🔫 Jangari", "🔮 Fantastika", "🎭 Drama"],
     "image": "https://images.pexels.com/photos/436413/pexels-photo-436413.jpeg?auto=compress&w=1200"},
    {"text": "Siz nonushta uchun nima yeyishni afzal ko'rasiz?", "ask_friend": "Siz nonushta uchun nima yeyishni afzal ko'rasiz?",
     "options": ["🍳 Tuxum", "🥣 Kasha", "🥐 Non", "🍎 Meva", "☕ Faqat kofe", "🚫 Nonushta qilmayman"],
     "image": "https://images.pexels.com/photos/103124/pexels-photo-103124.jpeg?auto=compress&w=1200"},
    {"text": "Siz pul topganda birinchi navbatda nima qilasiz?", "ask_friend": "Siz pul topganda birinchi navbatda nima qilasiz?",
     "options": ["💰 Jamg'araman", "🛍 Xarid qilaman", "🎁 Yaqinlarimga sovg'a", "✈️ Sayohatga ketaman", "📈 Investitsiya"],
     "image": "https://images.pexels.com/photos/4386431/pexels-photo-4386431.jpeg?auto=compress&w=1200"},
    {"text": "Siz qanday kiyinishni yaxshi ko'rasiz?", "ask_friend": "Siz qanday kiyinishni yaxshi ko'rasiz?",
     "options": ["👔 Rasmiy", "👕 Casual", "🧥 Sport", "🎨 Original va o'ziga xos"],
     "image": "https://images.pexels.com/photos/1598507/pexels-photo-1598507.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi mavsum uchun ko'proq pul sarflaysiz?", "ask_friend": "Siz qaysi mavsum uchun ko'proq pul sarflaysiz?",
     "options": ["🌸 Bahor", "☀️ Yoz", "🍂 Kuz", "❄️ Qish"],
     "image": "https://images.pexels.com/photos/3621344/pexels-photo-3621344.jpeg?auto=compress&w=1200"},
    {"text": "Siz odatda qachon uyg'onasiz?", "ask_friend": "Siz odatda qachon uyg'onasiz?",
     "options": ["🌅 5-7 da", "🌄 7-9 da", "🌞 9-11 da", "🌝 11 dan keyin"],
     "image": "https://images.pexels.com/photos/914910/pexels-photo-914910.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi sport turini yaxshi ko'rasiz?", "ask_friend": "Siz qaysi sport turini yaxshi ko'rasiz?",
     "options": ["⚽ Futbol", "🏀 Basketbol", "🎾 Tennis", "🏊 Suzish", "🥊 Boks", "🏋️ Fitness", "🚴 Velosiped", "🚫 Sportni yoqtirmayman"],
     "image": "https://images.pexels.com/photos/46798/the-ball-stadion-football-the-pitch-46798.jpeg?auto=compress&w=1200"},
    {"text": "Sizning sevimli ovqatingiz?", "ask_friend": "Sizning sevimli ovqatingiz?",
     "options": ["🍕 Pizza", "🍜 Makaron", "🍱 Sushi", "🥗 Salat", "🍖 Go'sht", "🥘 Osh", "🍔 Burger"],
     "image": "https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi tilni bilasiz?", "ask_friend": "Siz qaysi tilni bilasiz?",
     "options": ["🇺🇿 O'zbek", "🇷🇺 Rus", "🇬🇧 Ingliz", "🇰🇷 Koreys", "🇹🇷 Turk", "🇩🇪 Nemis", "🌍 Boshqa"],
     "image": "https://images.pexels.com/photos/267669/pexels-photo-267669.jpeg?auto=compress&w=1200"},
    {"text": "Siz qanday maqsadga egasiz?", "ask_friend": "Siz qanday maqsadga egasiz?",
     "options": ["💼 Karyera", "👨‍👩‍👧 Oila", "💰 Boylik", "🌍 Sayohat", "🎓 Bilim", "😊 Baxt"],
     "image": "https://images.pexels.com/photos/3758105/pexels-photo-3758105.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi vaqtda eng sermahsul bo'lasiz?", "ask_friend": "Siz qaysi vaqtda eng sermahsul bo'lasiz?",
     "options": ["🌅 Ertalab", "🌞 Kunduzi", "🌆 Kechqurun", "🌙 Kechasi"],
     "image": "https://images.pexels.com/photos/1181671/pexels-photo-1181671.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi ijtimoiy tarmoqdan ko'proq foydalanasiz?", "ask_friend": "Siz qaysi ijtimoiy tarmoqdan ko'proq foydalanasiz?",
     "options": ["📸 Instagram", "🎵 TikTok", "✈️ Telegram", "🐦 Twitter/X", "▶️ YouTube", "📘 Facebook"],
     "image": "https://images.pexels.com/photos/607812/pexels-photo-607812.jpeg?auto=compress&w=1200"},
    {"text": "Do'stingiz xato qilsa siz nima qilasiz?", "ask_friend": "Do'stingiz xato qilsa siz nima qilasiz?",
     "options": ["💬 To'g'ridan aytaman", "🤗 Yumshoq tarzda aytaman", "🤐 Jimgina qolaman", "😄 Kulgiga olaman"],
     "image": "https://images.pexels.com/photos/1024311/pexels-photo-1024311.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi his-tuyg'uni ko'proq his qilasiz?", "ask_friend": "Siz qaysi his-tuyg'uni ko'proq his qilasiz?",
     "options": ["😊 Xursandchilik", "😔 G'amginlik", "😤 G'azab", "😨 Xavotir", "😐 Befarqlik"],
     "image": "https://images.pexels.com/photos/3808039/pexels-photo-3808039.jpeg?auto=compress&w=1200"},
    {"text": "Siz qanday orzuga egasiz?", "ask_friend": "Siz qanday orzuga egasiz?",
     "options": ["🌍 Dunyo sayrini qilish", "🏠 O'z uyim bo'lsin", "💼 Katta kompaniya ochish", "🎨 Mashhur bo'lish", "👨‍👩‍👧 Baxtli oila"],
     "image": "https://images.pexels.com/photos/1051838/pexels-photo-1051838.jpeg?auto=compress&w=1200"},
    {"text": "Siz qanday o'rganishni yaxshi ko'rasiz?", "ask_friend": "Siz qanday o'rganishni yaxshi ko'rasiz?",
     "options": ["📖 Kitob o'qib", "🎬 Video ko'rib", "🎧 Audio tinglash", "✍️ Yozib", "🧪 Amaliyot orqali"],
     "image": "https://images.pexels.com/photos/4050315/pexels-photo-4050315.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi mavzuda ko'proq gaplashishni yaxshi ko'rasiz?", "ask_friend": "Siz qaysi mavzuda ko'proq gaplashishni yaxshi ko'rasiz?",
     "options": ["🔬 Fan va texnologiya", "🎭 San'at va madaniyat", "⚽ Sport", "💼 Biznes", "❤️ Munosabatlar", "🌍 Siyosat"],
     "image": "https://images.pexels.com/photos/1181622/pexels-photo-1181622.jpeg?auto=compress&w=1200"},
    {"text": "Siz qanday fikrlovchisiz?", "ask_friend": "Siz qanday fikrlovchisiz?",
     "options": ["🧠 Mantiqiy", "❤️ His-tuyg'uga asoslanaman", "⚖️ Ikkalasini balanslashtiram", "🎲 Intuitiv"],
     "image": "https://images.pexels.com/photos/3758756/pexels-photo-3758756.jpeg?auto=compress&w=1200"},
    {"text": "Siz qanday muloqot qilishni afzal ko'rasiz?", "ask_friend": "Siz qanday muloqot qilishni afzal ko'rasiz?",
     "options": ["💬 Yozma xabar", "📞 Telefon qo'ng'irog'i", "🤝 Yuzma-yuz", "🎥 Video qo'ng'iroq"],
     "image": "https://images.pexels.com/photos/1591062/pexels-photo-1591062.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi mavsumda tug'ilganingizga ko'ra o'zingizni qanday his qilasiz?", "ask_friend": "Siz qaysi mavsumda tug'ilganingizga ko'ra o'zingizni qanday his qilasiz?",
     "options": ["🌸 Bahor bolasi", "☀️ Yoz bolasi", "🍂 Kuz bolasi", "❄️ Qish bolasi"],
     "image": "https://images.pexels.com/photos/34763/pexels-photo.jpg?auto=compress&w=1200"},
    {"text": "Siz hayotda nimani eng muhim deb hisoblaysiz?", "ask_friend": "Siz hayotda nimani eng muhim deb hisoblaysiz?",
     "options": ["❤️ Muhabbat", "💰 Pul", "🏥 Sog'liq", "🎓 Bilim", "👨‍👩‍👧 Oila", "🌍 Erkinlik"],
     "image": "https://images.pexels.com/photos/2781814/pexels-photo-2781814.jpeg?auto=compress&w=1200"},
    {"text": "Siz qaysi davlatda yashashni orzulaysiz?", "ask_friend": "Siz qaysi davlatda yashashni orzulaysiz?",
     "options": ["🇺🇿 O'zbekiston", "🇰🇷 Janubiy Koreya", "🇺🇸 AQSh", "🇬🇧 Britaniya", "🇩🇪 Germaniya", "🇦🇪 BAA", "🇹🇷 Turkiya", "🌍 Boshqa"],
     "image": "https://images.pexels.com/photos/1008155/pexels-photo-1008155.jpeg?auto=compress&w=1200"},
]

COMPAT_QUESTIONS_FREE_COUNT = 24
COMPAT_QUESTIONS_PREMIUM_COUNT = len(COMPAT_QUESTIONS)

_img_cache = {}

def get_question_image(url):
    if url in _img_cache:
        return _img_cache[url]
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            img = Image.open(io.BytesIO(r.content))
            img = img.resize((1280, 640), Image.LANCZOS)
            _img_cache[url] = img
            return img
    except Exception as e:
        log.error(f"Rasm yuklash xatosi: {e}")
    img = Image.new('RGB', (1280, 640), '#1a1a2e')
    return img

def create_question_image(question_index):
    try:
        q = COMPAT_QUESTIONS[question_index % len(COMPAT_QUESTIONS)]
        img = get_question_image(q['image'])
        overlay = Image.new('RGBA', (1280, 640), (0, 0, 0, 100))
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        buf = io.BytesIO()
        img.save(buf, 'JPEG', quality=90)
        buf.seek(0)
        return buf
    except:
        buf = io.BytesIO()
        img = Image.new('RGB', (1280, 640), '#2d2d4a')
        draw = ImageDraw.Draw(img)
        try:
            font = lf(40, True)
            draw.text((640, 320), f"Savol {question_index+1}", fill='#ffffff', anchor='mm')
        except:
            pass
        img.save(buf, 'JPEG', quality=85)
        buf.seek(0)
        return buf

MBTI_QUESTIONS = [
    ("EI","Katta davralarda o'zingizni qanday his qilasiz?","😊 Energiya olaman","😌 Charchayman"),
    ("EI","Bo'sh vaqtda nima qilishni afzal ko'rasiz?","👥 Do'stlar bilan chiqaman","🏠 Uyda dam olaman"),
    ("EI","Yangi odamlar bilan tanishish sizga...","⚡ Oson va qiziqarli","😅 Bir oz qiyin"),
    ("EI","Muammo bo'lganda...","🗣 Birov bilan gaplashaman","🤔 O'zim o'ylayman"),
    ("EI","Siz o'zingizni...","🌟 Ochiq va faol","🌙 Xotirjam va kamgap"),
    ("EI","Telefonni olib gaplashish sizga...","📱 Yoqadi","💬 SMS yozishni afzal ko'raman"),
    ("EI","Katta to'y yoki partiyadasiz. Sizga...","🎉 Juda yaxshi, hayajonliyam","😮‍💨 Charchagan bo'laman"),
    ("EI","O'qish/ishlashda sizga qulay...","👨‍👩‍👧 Guruh bilan","🧍 Yolg'iz"),
    ("EI","Ko'proq qaysinisiz?","🗣 Ko'p gapiraman","👂 Ko'p tinglayman"),
    ("EI","Tanish bo'lmagan odamlar bilan muloqot...","😁 Yoqadi, yangi do'st!","😬 Biroz noqulay"),
    ("SN","Yangi narsa o'rganayotganda...","📋 Qadamma-qadam amal qilaman","🔭 Umumiy manzarani tushunmoqchiman"),
    ("SN","Siz ko'proq...","🔍 Hozirgi faktlarga ishonaman","💭 Kelajak imkoniyatlarini o'ylayman"),
    ("SN","Qo'llanmani o'qishda...","📖 Har bir qadamni o'qiyman","⏩ Asosiy g'oyani tezda tushunaman"),
    ("SN","Siz ko'proq...","🛠 Amaliy va aniq","🎨 Ijodiy va mavhum"),
    ("SN","Tajriba va intuitsiyadan qaysinisiga ko'proq ishonasiz?","📊 Tajriba va faktlarga","✨ Ichki sezgiga"),
    ("SN","Yangi loyihada...","📐 Aniq reja tuzaman","🚀 Ko'rgan sari harakat qilaman"),
    ("SN","Ko'proq qiziqasiz...","🔧 Qanday ishlashi","💡 Nima uchun ishlashi"),
    ("SN","Tasavvuringiz...","🏔 Aniq va real narsalarda","🌈 Fantaziya va ehtimollarda"),
    ("SN","Muammoni hal qilishda...","✅ Oldin muvaffaqiyatli usulni qo'llayman","🔄 Yangi yechim izlayman"),
    ("SN","Ko'proq qaysisiz?","📌 Detalchi","🗺 Umumiychi"),
    ("TF","Qaror qabul qilganda...","🧠 Mantiqqa asoslanaman","❤️ His-tuyg'uga asoslanaman"),
    ("TF","Birov xato qilsa...","📢 To'g'ridan-to'g'ri aytaman","🤗 Yumshoq tarzda aytaman"),
    ("TF","Siz uchun muhimroq...","⚖️ Adolat va haqiqat","🕊 Uyg'unlik va tinchlik"),
    ("TF","Muhokamada...","💪 G'alaba qozonishni xohlayman","🤝 Hammani rozi qilmoqchiman"),
    ("EI","Siz ko'proq qayerda energiya olasiz?","🌍 Tashqi dunyodan — odamlar, hodisalar","🧘 Ichki dunyomdan — fikrlar, his-tuyg'ular"),
    ("EI","Ijtimoiy tadbirdan keyin...","⚡ Yanada sergayrab bo'laman","😴 Dam olish kerak bo'ladi"),
    ("EI","Siz telefonda uzoq gaplasha olasizmi?","📱 Ha, yoqadi","⏱ Faqat kerak bo'lganda"),
    ("SN","Siz tushlarni eslab qolasizmi?","🌙 Ha, tez-tez","😴 Deyarli yo'q"),
    ("SN","Siz ko'proq nimalarga e'tibor berasiz?","🔍 Tafsilotlarga","🌐 Umumiy manzaraga"),
    ("SN","Siz qaysi turdagi kitoblarni yaxshi ko'rasiz?","📰 Haqiqiy voqealar asosida","🌌 Fantastika va xayoliy"),
    ("TF","Siz muhim qarorni qanday qabul qilasiz?","📊 Ma'lumot tahlil qilib","💭 Ichki his bilan"),
    ("TF","Siz do'stingizning muammosini eshitganda...","💡 Yechim taklif qilaman","🤗 Birinchi tinglayman va qo'llab-quvvatlayman"),
    ("TF","Bahslashishda siz...","🎯 G'alaba muhim","🤝 Munosabat muhim"),
    ("JP","Siz reja tuzishni yaxshi ko'rasizmi?","📅 Ha, oldindan rejalashtirishni yaxshi ko'raman","🌊 Yo'q, spontan bo'lishni afzal ko'raman"),
    ("JP","Muddatlar haqida...","⏰ Har doim o'z vaqtida topshiraman","⚡ Oxirgi daqiqada yaxshi ishlayam"),
    ("JP","Uyingiz odatda qanday?","🗂 Tartiblangan va aniq joyida","🎨 Tartibsiz, lekin o'zim topaman"),
    ("JP","Siz yangi loyihani boshlashda...","📋 Dastlab batafsil reja tuzaman","🚀 To'g'ridan-to'g'ri boshlayman"),
    ("JP","Siz o'zingizni qanday his qilasiz?","📌 Tizimli va tartibli","🌈 Erkin va moslashuvchan"),
    ("JP","Kutilmagan o'zgarishlarga...","😟 Qiynalaman, tartib yaxshi","😊 Yaxshi moslashaman"),
    ("EI","Siz yangi shahar/mamlakatga borganda...","🗺 Odamlar bilan tanishaman","📸 Yolg'iz sayr qilaman"),
    ("SN","Yangi ish o'rganishda eng qiyin narsa?","📖 Ko'p ma'lumot eslab qolish","🔭 Katta manzarani tushunish"),
    ("TF","Siz birovni qanchalik tez kechirasiz?","💛 Tez, g'azab uzoq turmaydi","⏳ Vaqt kerak, shikoyat qoladi"),
    ("JP","Sayohatda siz...","🗓 Batafsil dastur tuzib ketaman","🎒 Erkin, ko'rganimcha ketaman"),
    ("EI","Siz ko'proq qaysi vaziyatda o'zingizni yaxshi his qilasiz?","🎤 Ko'pchilik oldida gaplashish","✍️ Yozma muloqot"),
    ("SN","Siz qaysi turdagi musiqa tinglaysiz?","🎵 Matn va hikoya muhim","🎧 Ritm va ohang muhim"),
    ("TF","Siz yangi qonun-qoidalarga...","✅ Ularga rioya qilaman","🤔 Mantiqini tushunib, keyin qaror qilaman"),
    ("JP","Siz ish/o'qishni...","🌅 Ertalab bajarishni afzal ko'raman","🌙 Kechqurun bajarishni afzal ko'raman"),
    ("EI","Siz yolg'iz ishlashni yaxshi ko'rasizmi?","🧍 Ha, yolg'iz samaraliroq","👥 Yo'q, jamoa bilan yaxshiroq"),
    ("SN","Siz birovni tushuntirishda...","📌 Aniq misol keltiram","💡 Umumiy g'oyani beraman"),
    ("TF","Siz tanqid eshitganda...","💪 Rag'bat sifatida qabul qilaman","😔 Biroz ranjiyaman"),
    ("JP","Siz xonangizni qanday tartibga solasiz?","🗂 Har narsaning o'z joyi bor","📦 Kerak bo'lganda yig'ishtiraman"),
]

MBTI_QUESTIONS_FREE_COUNT = 24
MBTI_QUESTIONS_PREMIUM_COUNT = len(MBTI_QUESTIONS)

MBTI_DESCRIPTIONS = {
    'INTJ':{'name':'Arxitektor','emoji':'🏛','short':'Strategik fikrlovchi. Maqsadga yo\'llovchi va mustaqil shaxs.'},
    'INTP':{'name':'Mantiqchi','emoji':'🔬','short':'Intellektual qiziquvchan, nazariyalar va tahlil sevuvchi.'},
    'ENTJ':{'name':'Komandant','emoji':'👑','short':'Qat\'iyatli va charismatik lider.'},
    'ENTP':{'name':'Muhokamachi','emoji':'⚡','short':'Aqlli va qiziquvchan, yangi yechim topadi.'},
    'INFJ':{'name':'Himoyachi','emoji':'🌟','short':'Idealist va sezgir.'},
    'INFP':{'name':'Vositachi','emoji':'🌸','short':'Ijodiy va idealizmga moyil.'},
    'ENFJ':{'name':'Protagonist','emoji':'🎭','short':'Xarizmatik va ilhomlantiruvchi lider.'},
    'ENFP':{'name':'Kampaniyachi','emoji':'🎨','short':'Erkin va ijodiy ruh.'},
    'ISTJ':{'name':'Logist','emoji':'📋','short':'Mas\'uliyatli va ishonchli.'},
    'ISFJ':{'name':'Mudofaachi','emoji':'🛡','short':'Issiqqo\'l va g\'amxo\'r.'},
    'ESTJ':{'name':'Ijrochi','emoji':'⚙️','short':'Tartibli va samarali tashkilotchi.'},
    'ESFJ':{'name':'Konsul','emoji':'🤝','short':'Mehmondo\'st va g\'amxo\'r.'},
    'ISTP':{'name':'Virtuoz','emoji':'🔧','short':'Amaliy muammolarni osongina hal qiladi.'},
    'ISFP':{'name':'Sarguzashtchi','emoji':'🌿','short':'Ijodiy va sezgir.'},
    'ESTP':{'name':'Tadbirkor','emoji':'🚀','short':'Energetik va amaliy.'},
    'ESFP':{'name':'Eğlentiruvchi','emoji':'🎉','short':'Hayotsevar va spontan.'},
}

MBTI_PREMIUM_DETAILS = {
    'INTJ': {'detail': ("🏛 *INTJ — Arxitektor*\n\n📊 *Shkala foizlari:*\n  • Introvert (I): ichki dunyoga yo'nalgan\n  • Intuitsiya (N): kelajak va imkoniyatlarga e'tibor\n  • Mantiq (T): qarorlarni ratsional qabul qiladi\n  • Rejali (J): tizimli va maqsadli harakat qiladi\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 🔬 Olim / Tadqiqotchi\n  2. 💻 Dasturchi / Muhandis\n  3. 📊 Strategik menejment\n  4. ⚖️ Huquqshunos / Advokat\n  5. 🏦 Moliyaviy tahlilchi\n\n💚 *Mos tiplar:* ENFP, ENTP, INFJ\n❤️ *To'qnashuv:* ESFP, ESFJ\n\n🌟 *Kuchli tomonlar:* Strategik fikrlash, mustaqillik, qat'iyat\n⚠️ *Zaif tomonlar:* Ba'zan sovuqqon ko'rinishi, perfektsionizm")},
    'INTP': {'detail': ("🔬 *INTP — Mantiqchi*\n\n📊 *Shkala foizlari:*\n  • Introvert (I): chuqur fikrlashni afzal ko'radi\n  • Intuitsiya (N): abstrak g'oyalarga qiziqadi\n  • Mantiq (T): ob'ektiv tahlil qiladi\n  • Moslashuvchan (P): ochiq va erkin fikrli\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 🔭 Olim / Tadqiqotchi\n  2. 💻 Dasturchi\n  3. 📐 Matematik\n  4. 🧠 Faylasuf\n  5. 🎓 O'qituvchi / Professor\n\n💚 *Mos tiplar:* ENTJ, ESTJ, ENFJ\n❤️ *To'qnashuv:* ESFJ, ISFJ\n\n🌟 *Kuchli tomonlar:* Tahliliy fikrlash, ijodkorlik, ob'ektivlik\n⚠️ *Zaif tomonlar:* Prokrastinatsiya, his-tuyg'ularni ifodalash qiyinligi")},
    'ENTJ': {'detail': ("👑 *ENTJ — Komandant*\n\n📊 *Shkala foizlari:*\n  • Ekstrovert (E): odamlar bilan energiya oladi\n  • Intuitsiya (N): kelajakni ko'ra oladi\n  • Mantiq (T): samarali qaror qabul qiladi\n  • Rejali (J): maqsadga yo'nalgan harakat\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 👔 CEO / Bosh direktor\n  2. ⚖️ Huquqshunos\n  3. 📊 Biznes strategist\n  4. 🏗 Loyiha menejeri\n  5. 🎓 Universitet professori\n\n💚 *Mos tiplar:* INTP, INFP, ENFP\n❤️ *To'qnashuv:* ISFP, INFP\n\n🌟 *Kuchli tomonlar:* Liderlik, samaradorlik, ishontirish\n⚠️ *Zaif tomonlar:* Sabrsizlik, hokimiyatparast ko'rinishi")},
    'ENTP': {'detail': ("⚡ *ENTP — Muhokamachi*\n\n📊 *Shkala foizlari:*\n  • Ekstrovert (E): yangi odamlardan ilhom oladi\n  • Intuitsiya (N): yangi g'oyalarni yaxshi ko'radi\n  • Mantiq (T): ratsional va tanqidiy fikrlaydi\n  • Moslashuvchan (P): spontan va erkin\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 💡 Tadbirkor / Startaper\n  2. ⚖️ Advokat\n  3. 🎨 Kreativ direktor\n  4. 📢 Marketolog\n  5. 🔬 Muhandis\n\n💚 *Mos tiplar:* INTJ, INFJ, ENFJ\n❤️ *To'qnashuv:* ISFJ, ISTJ\n\n🌟 *Kuchli tomonlar:* Ijodkorlik, debat mahorati, moslashuvchanlik\n⚠️ *Zaif tomonlar:* Nizoga moyillik, e'tiborsizlik")},
    'INFJ': {'detail': ("🌟 *INFJ — Himoyachi*\n\n📊 *Shkala foizlari:*\n  • Introvert (I): yolg'izlikda kuch to'playdi\n  • Intuitsiya (N): chuqur ma'no izlaydi\n  • His-tuyg'u (F): odamlarga g'amxo'r\n  • Rejali (J): maqsadga intiladi\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 🧠 Psixolog / Terapevist\n  2. ✍️ Yozuvchi\n  3. 👩‍🏫 O'qituvchi\n  4. 🌿 Ijtimoiy ishchi\n  5. 🎨 San'atkor\n\n💚 *Mos tiplar:* ENFP, ENTP, INTJ\n❤️ *To'qnashuv:* ESTP, ESFP\n\n🌟 *Kuchli tomonlar:* Empatiya, ilhom berish, chuqur fikrlash\n⚠️ *Zaif tomonlar:* Ortiqcha his qilish, charchash")},
    'INFP': {'detail': ("🌸 *INFP — Vositachi*\n\n📊 *Shkala foizlari:*\n  • Introvert (I): yolg'izlikda energiya oladi\n  • Intuitsiya (N): imkoniyat va ma'nolarga e'tibor\n  • His-tuyg'u (F): qadriyatlarga asoslanadi\n  • Moslashuvchan (P): erkin va ochiq\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. ✍️ Yozuvchi / Shoir\n  2. 🎨 Rassom / Dizayner\n  3. 🧠 Psixolog\n  4. 👩‍🏫 O'qituvchi\n  5. 🌍 NGO xodimi\n\n💚 *Mos tiplar:* ENFJ, ENTJ, INFJ\n❤️ *To'qnashuv:* ESTJ, ENTJ\n\n🌟 *Kuchli tomonlar:* Ijodkorlik, sadoqat, empatiya\n⚠️ *Zaif tomonlar:* Ortiqcha idealizm, o'z-o'zini tanqid")},
    'ENFJ': {'detail': ("🎭 *ENFJ — Protagonist*\n\n📊 *Shkala foizlari:*\n  • Ekstrovert (E): odamlardan energiya oladi\n  • Intuitsiya (N): odamlarning salohiyatini ko'radi\n  • His-tuyg'u (F): munosabatlarni qadrlaydi\n  • Rejali (J): tashkilotchilik xususiyati\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 🎓 O'qituvchi / Murabbiy\n  2. 📢 PR va kommunikatsiya\n  3. 👨‍💼 HR menejeri\n  4. 🌍 Siyosatchi\n  5. 🧠 Hayot murabbiy (life coach)\n\n💚 *Mos tiplar:* INFP, INTP, ISFP\n❤️ *To'qnashuv:* ISTP, INTP\n\n🌟 *Kuchli tomonlar:* Ilhomlantirish, empatiya, tashkilotchilik\n⚠️ *Zaif tomonlar:* Ortiqcha boshqarishga intilish, o'z ehtiyojlarini unutish")},
    'ENFP': {'detail': ("🎨 *ENFP — Kampaniyachi*\n\n📊 *Shkala foizlari:*\n  • Ekstrovert (E): odamlar bilan jonlanadi\n  • Intuitsiya (N): yangi g'oyalar va imkoniyatlar\n  • His-tuyg'u (F): qadriyatlarga sodiq\n  • Moslashuvchan (P): spontan va erkin ruh\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 🎨 Kreativ direktor\n  2. 📢 Jurnalist / Blogger\n  3. 🎭 Aktyor / Rejissyor\n  4. 🧠 Psixolog\n  5. 💡 Tadbirkor\n\n💚 *Mos tiplar:* INTJ, INFJ, ENFJ\n❤️ *To'qnashuv:* ISTJ, ISFJ\n\n🌟 *Kuchli tomonlar:* Ijodkorlik, ilhom, muloqot mahorati\n⚠️ *Zaif tomonlar:* Diqqat tarqoqligi, haddan ortiq optimizm")},
    'ISTJ': {'detail': ("📋 *ISTJ — Logist*\n\n📊 *Shkala foizlari:*\n  • Introvert (I): yolg'izlikda ishlashni afzal ko'radi\n  • Sezgi (S): aniq faktlarga asoslanadi\n  • Mantiq (T): ob'ektiv qaror qiladi\n  • Rejali (J): tizimli va tartibli\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 📊 Buxgalter / Auditor\n  2. ⚖️ Huquqshunos\n  3. 🏦 Bankir\n  4. 💻 IT administrator\n  5. 🏗 Loyiha menejeri\n\n💚 *Mos tiplar:* ESFP, ESTP, ISFJ\n❤️ *To'qnashuv:* ENFP, ENTP\n\n🌟 *Kuchli tomonlar:* Ishonchlilik, mas'uliyat, tartib\n⚠️ *Zaif tomonlar:* Qat'iylik, o'zgarishlarga qarshilik")},
    'ISFJ': {'detail': ("🛡 *ISFJ — Mudofaachi*\n\n📊 *Shkala foizlari:*\n  • Introvert (I): tinch muhitni yaxshi ko'radi\n  • Sezgi (S): tafsilotlarga e'tibor beradi\n  • His-tuyg'u (F): odamlarga g'amxo'r\n  • Rejali (J): tizimli va puxta\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 👩‍⚕️ Hamshira / Shifokor\n  2. 👩‍🏫 O'qituvchi\n  3. 🌿 Ijtimoiy ishchi\n  4. 📚 Kutubxonachi\n  5. 🏠 Admin / Kotib\n\n💚 *Mos tiplar:* ESTP, ESFP, ISTJ\n❤️ *To'qnashuv:* ENTP, ESTP\n\n🌟 *Kuchli tomonlar:* G'amxo'rlik, sadoqat, sabr\n⚠️ *Zaif tomonlar:* O'zini ikkinchi o'ringa qo'yish, o'zgarishlarga qiynalish")},
    'ESTJ': {'detail': ("⚙️ *ESTJ — Ijrochi*\n\n📊 *Shkala foizlari:*\n  • Ekstrovert (E): faol va tashabbuskor\n  • Sezgi (S): amaliy va real\n  • Mantiq (T): adolatli va qat'iy\n  • Rejali (J): tartib va qoida muhim\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 👔 Menejer / Direktor\n  2. ⚖️ Hakim / Prokuror\n  3. 🏗 Qurilish menejeri\n  4. 🏦 Bank direktori\n  5. 🎓 Ma'muriyat rahbari\n\n💚 *Mos tiplar:* INTP, ISTP, ISFP\n❤️ *To'qnashuv:* INFP, ENFP\n\n🌟 *Kuchli tomonlar:* Tashkilotchilik, mas'uliyat, qat'iylik\n⚠️ *Zaif tomonlar:* Moslashmaganlik, hissiyotni e'tiborsiz qoldirish")},
    'ESFJ': {'detail': ("🤝 *ESFJ — Konsul*\n\n📊 *Shkala foizlari:*\n  • Ekstrovert (E): odamlar bilan energiya oladi\n  • Sezgi (S): hozirgi vaqtga e'tibor\n  • His-tuyg'u (F): munosabatlarni qadrlaydi\n  • Rejali (J): tartibli va puxta\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 👩‍⚕️ Hamshira / Shifokor\n  2. 👩‍🏫 O'qituvchi\n  3. 📢 PR mutaxassisi\n  4. 🏪 Savdo menejeri\n  5. 🌿 Ijtimoiy ishchi\n\n💚 *Mos tiplar:* ISFP, ISTP, ESFJ\n❤️ *To'qnashuv:* INTP, ISTP\n\n🌟 *Kuchli tomonlar:* Mehmondo'stlik, g'amxo'rlik, tashkilotchilik\n⚠️ *Zaif tomonlar:* Tanqidga sezgirlik, boshqalarga ortiqcha qaram bo'lish")},
    'ISTP': {'detail': ("🔧 *ISTP — Virtuoz*\n\n📊 *Shkala foizlari:*\n  • Introvert (I): yolg'iz kuzatishni afzal ko'radi\n  • Sezgi (S): amaliy va aniq\n  • Mantiq (T): samarali yechim topadi\n  • Moslashuvchan (P): spontan va erkin\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 🔧 Mexanik / Muhandis\n  2. 💻 Dasturchi\n  3. 🚒 O't o'chiruvchi\n  4. ✈️ Pilot\n  5. 🔬 Laboratoriya texnigi\n\n💚 *Mos tiplar:* ESFJ, ESTJ, ISTP\n❤️ *To'qnashuv:* ENFJ, INFJ\n\n🌟 *Kuchli tomonlar:* Amaliy mahorat, moslashuvchanlik, sovuqqonlik\n⚠️ *Zaif tomonlar:* Izolyatsiyaga moyillik, his-tuyg'ularni ifodalash qiyinligi")},
    'ISFP': {'detail': ("🌿 *ISFP — Sarguzashtchi*\n\n📊 *Shkala foizlari:*\n  • Introvert (I): ichki dunyosi boy\n  • Sezgi (S): go'zallik va tafsilotlarni his qiladi\n  • His-tuyg'u (F): qadriyatlarga sadiq\n  • Moslashuvchan (P): hozirgi lahzada yashaydi\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 🎨 Rassom / Dizayner\n  2. 📸 Fotograf\n  3. 🎵 Musiqachi\n  4. 👩‍⚕️ Hamshira\n  5. 🌿 Tabiat tadqiqotchisi\n\n💚 *Mos tiplar:* ENFJ, ESFJ, ISFP\n❤️ *To'qnashuv:* ESTJ, ENTJ\n\n🌟 *Kuchli tomonlar:* Ijodkorlik, empatiya, moslashuvchanlik\n⚠️ *Zaif tomonlar:* Muloqotda qiynalish, muddatlarni o'tkazib yuborish")},
    'ESTP': {'detail': ("🚀 *ESTP — Tadbirkor*\n\n📊 *Shkala foizlari:*\n  • Ekstrovert (E): harakatda energiya oladi\n  • Sezgi (S): haqiqiy dunyo bilan ishlaydi\n  • Mantiq (T): mantiqiy va ob'ektiv\n  • Moslashuvchan (P): spontan va tez qaror qiladi\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 💼 Tadbirkor\n  2. 🚔 Politsiyachi\n  3. 🏦 Broker / Treydir\n  4. ⚽ Professional sportchi\n  5. 🎤 Yurist / Notarius\n\n💚 *Mos tiplar:* ISFJ, ISTJ, ESTP\n❤️ *To'qnashuv:* INFJ, INTJ\n\n🌟 *Kuchli tomonlar:* Tez qaror, moslashuvchanlik, amaliylik\n⚠️ *Zaif tomonlar:* Sabrsizlik, uzoq muddatli rejalashtirish qiyinligi")},
    'ESFP': {'detail': ("🎉 *ESFP — Eğlentiruvchi*\n\n📊 *Shkala foizlari:*\n  • Ekstrovert (E): odamlar bilan jonlanadi\n  • Sezgi (S): hozirgi lahzada yashaydi\n  • His-tuyg'u (F): munosabatlarni qadrlaydi\n  • Moslashuvchan (P): spontan va hayotsevar\n\n💼 *Tavsiya etiladigan kasblar:*\n  1. 🎭 Aktyor / Tomosha beruvchi\n  2. 🎵 Musiqachi\n  3. 📢 PR / Marketing\n  4. 👩‍🏫 O'qituvchi (boshlang'ich)\n  5. 🍽 Restoran menejeri\n\n💚 *Mos tiplar:* ISTJ, ISFJ, ESFP\n❤️ *To'qnashuv:* INTJ, INFJ\n\n🌟 *Kuchli tomonlar:* Hayotsevarlik, muloqot, spontanlik\n⚠️ *Zaif tomonlar:* Uzoq muddatli rejalashtirish qiyinligi, haddan ortiq hissiyot")},
}

MBTI_COMPAT = {
    'INTJ':['ENFP','ENTP','INFJ','INTJ'], 'INTP':['ENTJ','ESTJ','ENFJ','INTP'],
    'ENTJ':['INTP','INFP','ENFP','ENTJ'], 'ENTP':['INTJ','INFJ','ENFJ','ENTP'],
    'INFJ':['ENFP','ENTP','INTJ','INFJ'], 'INFP':['ENFJ','ENTJ','INFJ','INFP'],
    'ENFJ':['INFP','INTP','ISFP','ENFJ'], 'ENFP':['INTJ','INFJ','ENFP','ENFJ'],
    'ISTJ':['ESFP','ESTP','ISFJ','ISTJ'], 'ISFJ':['ESTP','ESFP','ISTJ','ISFJ'],
    'ESTJ':['INTP','ISTP','ISFP','ESTJ'], 'ESFJ':['ISFP','ISTP','ESFJ','ISFJ'],
    'ISTP':['ESFJ','ESTJ','ISTP','ESTP'], 'ISFP':['ENFJ','ESFJ','ISFP','INFP'],
    'ESTP':['ISFJ','ISTJ','ESTP','ISTP'], 'ESFP':['ISTJ','ISFJ','ESFP','ISFP'],
}

def get_mbti_questions_for_user(uid):
    if is_premium(uid):
        return MBTI_QUESTIONS[:MBTI_QUESTIONS_PREMIUM_COUNT]
    return MBTI_QUESTIONS[:MBTI_QUESTIONS_FREE_COUNT]

def get_compat_questions_count_for_user(uid):
    if is_premium(uid):
        return COMPAT_QUESTIONS_PREMIUM_COUNT
    return COMPAT_QUESTIONS_FREE_COUNT

def calculate_mbti(answers):
    scores = {'E':0,'I':0,'S':0,'N':0,'T':0,'F':0,'J':0,'P':0}
    for i, ans in enumerate(answers):
        if i >= len(MBTI_QUESTIONS): break
        dic = MBTI_QUESTIONS[i][0]
        if ans == 0: scores[dic[0]] += 1
        else: scores[dic[1]] += 1
    return ('E' if scores['E']>=scores['I'] else 'I') + \
           ('S' if scores['S']>=scores['N'] else 'N') + \
           ('T' if scores['T']>=scores['F'] else 'F') + \
           ('J' if scores['J']>=scores['P'] else 'P')

def calculate_mbti_percentages(answers):
    scores = {'E':0,'I':0,'S':0,'N':0,'T':0,'F':0,'J':0,'P':0}
    counts = {'EI':0,'SN':0,'TF':0,'JP':0}
    for i, ans in enumerate(answers):
        if i >= len(MBTI_QUESTIONS): break
        dic = MBTI_QUESTIONS[i][0]
        counts[dic] += 1
        if ans == 0: scores[dic[0]] += 1
        else: scores[dic[1]] += 1
    result = {}
    for pair in ['EI','SN','TF','JP']:
        total = counts[pair]
        if total > 0:
            result[pair[0]] = int(scores[pair[0]] / total * 100)
            result[pair[1]] = int(scores[pair[1]] / total * 100)
        else:
            result[pair[0]] = 50
            result[pair[1]] = 50
    return result

def db_get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row: return None
    cols = ['user_id','nickname','mbti_type','mbti_answers','profile_open','is_premium','premium_until','created_at']
    return dict(zip(cols, row))

def db_get_by_nick(nick):
    cursor.execute("SELECT * FROM users WHERE LOWER(nickname)=LOWER(?)", (nick,))
    row = cursor.fetchone()
    if not row: return None
    cols = ['user_id','nickname','mbti_type','mbti_answers','profile_open','is_premium','premium_until','created_at']
    return dict(zip(cols, row))

def db_upsert_user(uid, **kwargs):
    u = db_get_user(uid)
    if not u:
        cursor.execute(
            "INSERT INTO users(user_id,nickname,mbti_type,mbti_answers,profile_open,is_premium,premium_until,created_at) VALUES(?,?,?,?,1,0,?,?)",
            (uid, kwargs.get('nickname'), kwargs.get('mbti_type'), kwargs.get('mbti_answers'),
             kwargs.get('premium_until'), datetime.now().strftime("%Y-%m-%d %H:%M")))
    else:
        for k,v in kwargs.items():
            if v is not None:
                cursor.execute(f"UPDATE users SET {k}=? WHERE user_id=?", (v, uid))
    conn.commit()

def is_premium(uid):
    u = db_get_user(uid)
    if not u or not u['is_premium']: return False
    if u['premium_until']:
        try:
            return datetime.strptime(u['premium_until'], '%Y-%m-%d') >= datetime.now()
        except:
            return False
    return True

def get_partner(uid):
    cursor.execute(
        "SELECT * FROM relationships WHERE (from_id=? OR to_id=?) AND rel_type IN ('Sevishganlar','Zaks') AND status='active'",
        (uid, uid))
    row = cursor.fetchone()
    return row if row else None

def get_friends(uid):
    cursor.execute(
        "SELECT * FROM relationships WHERE (from_id=? OR to_id=?) AND rel_type='Yaqin do''st' AND status='active'",
        (uid, uid))
    return cursor.fetchall()

def other_id(rel, uid):
    return rel[2] if rel[1] == uid else rel[1]

def rel_type_emoji(rt):
    return {'Yaqin do\'st':'👫','Sevishganlar':'💑','Zaks':'💍'}.get(rt,'🤝')

user_sessions = {}
user_last_active = {}  # Online foydalanuvchilar uchun

def sess(cid): return user_sessions.get(cid,{})
def set_sess(cid, **kw): user_sessions.setdefault(cid,{}).update(kw)
def clear_sess(cid):
    if cid in user_sessions:
        del user_sessions[cid]

def get_user_name(u): return u.first_name or u.username or "Do'st"
def get_profile_photo(uid):
    try:
        p = bot.get_user_profile_photos(uid, limit=1)
        if p.total_count > 0: return p.photos[0][-1].file_id
    except: pass
    return None

def generate_test_id(): return f"s_{random.randint(1000000000, 9999999999)}"
def remove_keyboard():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(KeyboardButton("/start"))
    return m

def mk(options, prefix, row_width=4):
    markup = InlineKeyboardMarkup(row_width=row_width)
    btns = [InlineKeyboardButton(o, callback_data=f"{prefix}_{i}") for i, o in enumerate(options)]
    for i in range(0, len(btns), row_width):
        markup.row(*btns[i:i+row_width])
    return markup

# ============================================================
# create_result_image — qora dizayn
# ============================================================
def create_result_image(percentage, name1, name2, matches_list, photo1_id=None, photo2_id=None):
    import math as _math
    W, H = 1280, 760

    img = Image.new('RGB', (W, H), '#1a1a1a')
    draw = ImageDraw.Draw(img)
    for i in range(H):
        t = i / H
        r = int(26 + t * 10); g = int(26 + t * 10); b = int(30 + t * 12)
        draw.rectangle([(0, i), (W, i+1)], fill=(r, g, b))

    star_positions = [
        (60,60,14),(150,120,10),(1100,70,14),(1200,140,10),(950,50,12),
        (50,580,10),(1220,500,12),(390,710,8),(900,710,10),(650,40,7),
        (210,670,8),(1060,640,10),(300,90,9),(980,690,8),(70,350,7),
        (1240,360,9),(480,55,6),(820,48,7),(120,420,6),(1160,420,7),
    ]
    for sx, sy, ss in star_positions:
        for ao in [0, 45]:
            pts = []
            for a in range(4):
                ba = _math.radians(a * 90 + ao)
                ln = ss if ao == 0 else ss * 0.45
                pts.append((sx + _math.cos(ba) * ln, sy + _math.sin(ba) * ln))
            draw.polygon(pts, fill='#777777')

    banner_cx = W // 2
    by0 = 22; bw = 540; bh = 64
    bx0 = banner_cx - bw // 2; bx1 = banner_cx + bw // 2
    by1 = by0 + bh; mid_y = (by0 + by1) // 2; tip = 30
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=34, fill='#2a2a2a', outline='#777777', width=2)
    draw.polygon([(bx0, by0+4), (bx0-tip, mid_y), (bx0, by1-4)], fill='#2a2a2a')
    draw.line([(bx0, by0+4), (bx0-tip, mid_y), (bx0, by1-4)], fill='#777777', width=2)
    draw.polygon([(bx1, by0+4), (bx1+tip, mid_y), (bx1, by1-4)], fill='#2a2a2a')
    draw.line([(bx1, by0+4), (bx1+tip, mid_y), (bx1, by1-4)], fill='#777777', width=2)
    _tcx(draw, "\u2665  O\u2019xshashlik testi  \u2665", banner_cx, by0+14, lf(28, True), '#cccccc')

    BOX_W, BOX_H, AV = 260, 270, 190
    box_y = 115; lbx = 48; rbx = W - 48 - BOX_W

    def draw_dark_box(bx, by):
        draw.rounded_rectangle([bx, by, bx+BOX_W, by+BOX_H], radius=20, fill='#242424', outline='#666666', width=2)

    def draw_avatar(photo_id, bx, by):
        ax = bx + (BOX_W - AV) // 2; ay = by + 16
        if photo_id:
            try:
                fi = bot.get_file(photo_id)
                data = bot.download_file(fi.file_path)
                pil_av = Image.open(io.BytesIO(data)).resize((AV, AV), Image.LANCZOS).convert('RGBA')
                mask = Image.new('L', (AV, AV), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, AV, AV), fill=255)
                base = Image.new('RGBA', (AV, AV), (0, 0, 0, 0))
                base.paste(pil_av, mask=mask)
                img.paste(base, (ax, ay), mask=base.split()[3])
                draw.ellipse([ax-3, ay-3, ax+AV+3, ay+AV+3], outline='#888888', width=3)
                return
            except:
                pass
        draw.ellipse([ax, ay, ax+AV, ay+AV], fill='#333333', outline='#666666', width=3)
        cx_av = ax + AV // 2
        draw.ellipse([cx_av-28, ay+28, cx_av+28, ay+84], fill='#555555')
        draw.ellipse([cx_av-42, ay+AV//2+10, cx_av+42, ay+AV//2+90], fill='#555555')

    draw_dark_box(lbx, box_y); draw_avatar(photo1_id, lbx, box_y)
    draw_dark_box(rbx, box_y); draw_avatar(photo2_id, rbx, box_y)

    name_y = box_y + BOX_H + 10; name_h = 48
    for nm, bx in [(name1, lbx), (name2, rbx)]:
        draw.rounded_rectangle([bx, name_y, bx+BOX_W, name_y+name_h], radius=14, fill='#2a2a2a', outline='#666666', width=2)
        _tcx(draw, nm[:16], bx+BOX_W//2, name_y+10, lf(22, True), '#dddddd')

    cx = W // 2; cy = 470
    R_outer = 170; R_inner = 105; arc_thickness = R_outer - R_inner

    draw.arc([cx-R_outer, cy-R_outer, cx+R_outer, cy+R_outer], start=180, end=360, fill='#3a3a3a', width=arc_thickness)

    fill_angle = int(percentage * 1.8)
    if fill_angle > 0:
        for layer, col in enumerate(['#555555', '#888888', '#aaaaaa']):
            lr = R_outer - layer * 2; lt = arc_thickness - layer * 2
            draw.arc([cx-lr, cy-lr, cx+lr, cy+lr], start=180, end=180+fill_angle, fill=col, width=lt)
        draw.arc([cx-R_outer+6, cy-R_outer+6, cx+R_outer-6, cy+R_outer-6],
                 start=180, end=180+fill_angle, fill='#cccccc', width=arc_thickness-12)

    draw.arc([cx-R_outer-4, cy-R_outer-4, cx+R_outer+4, cy+R_outer+4], start=178, end=362, fill='#666666', width=3)
    draw.arc([cx-R_inner+4, cy-R_inner+4, cx+R_inner-4, cy+R_inner-4], start=178, end=362, fill='#555555', width=2)

    needle_angle = _math.radians(180 + fill_angle)
    needle_len = R_inner - 8
    nx = int(cx + needle_len * _math.cos(needle_angle))
    ny = int(cy + needle_len * _math.sin(needle_angle))
    draw.line([(cx, cy), (nx, ny)], fill='#ffffff', width=5)
    draw.ellipse([cx-8, cy-8, cx+8, cy+8], fill='#888888', outline='#cccccc', width=2)

    inner_r = R_inner - 6
    draw.ellipse([cx-inner_r, cy-inner_r, cx+inner_r, cy+inner_r], fill='#1e1e1e', outline='#555555', width=2)

    _tcx(draw, f"{percentage}%", cx, cy-58, lf(60, True), '#ffffff')
    _tcx(draw, "o\u2019xshashlik", cx, cy-4, lf(20), '#aaaaaa')
    _tcx(draw, "darajasi", cx, cy+22, lf(20), '#aaaaaa')
    _tcx(draw, "0%", cx - R_outer + 10, cy + 18, lf(20), '#777777')
    _tcx(draw, "100%", cx + R_outer - 10, cy + 18, lf(20), '#777777')

    if percentage <= 20:   label = "\u2665  G\u2019ayrioddiy uzoq  \u2665"
    elif percentage <= 40: label = "\u2665  Unchalik yaqin emas  \u2665"
    elif percentage <= 60: label = "\u2665  Yaqin odamlardir  \u2665"
    elif percentage <= 80: label = "\u2665  Yaxshi do\u2019stlar  \u2665"
    else:                  label = "\u2665  Ruhiy egizaklar!  \u2665"

    lbl_y = cy + R_inner + 28; lbl_w = 440; lbl_h = 56
    lbl_x0 = cx - lbl_w // 2; lbl_x1 = cx + lbl_w // 2
    lbl_mid = lbl_y + lbl_h // 2; lbl_tip = 26
    draw.rounded_rectangle([lbl_x0, lbl_y, lbl_x1, lbl_y+lbl_h], radius=28, fill='#2a2a2a', outline='#777777', width=2)
    draw.polygon([(lbl_x0, lbl_y+4), (lbl_x0-lbl_tip, lbl_mid), (lbl_x0, lbl_y+lbl_h-4)], fill='#2a2a2a')
    draw.line([(lbl_x0, lbl_y+4), (lbl_x0-lbl_tip, lbl_mid), (lbl_x0, lbl_y+lbl_h-4)], fill='#777777', width=2)
    draw.polygon([(lbl_x1, lbl_y+4), (lbl_x1+lbl_tip, lbl_mid), (lbl_x1, lbl_y+lbl_h-4)], fill='#2a2a2a')
    draw.line([(lbl_x1, lbl_y+4), (lbl_x1+lbl_tip, lbl_mid), (lbl_x1, lbl_y+lbl_h-4)], fill='#777777', width=2)
    _tcx(draw, label, cx, lbl_y+14, lf(24, True), '#cccccc')

    _tcx(draw, "@mbtiuzbot", cx, H - 34, lf(22, True), '#666666')

    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=96)
    buf.seek(0)
    return buf

MBTI_COLORS = {
    'INTJ':'#4a4e8c','INTP':'#5b7fa6','ENTJ':'#7b4f9e','ENTP':'#9b6ab5',
    'INFJ':'#3d7a6e','INFP':'#5aaa8c','ENFJ':'#e07040','ENFP':'#e89050',
    'ISTJ':'#5a6a7a','ISFJ':'#7a8a6a','ESTJ':'#8a6a4a','ESFJ':'#c07060',
    'ISTP':'#4a7a8a','ISFP':'#6a9a7a','ESTP':'#c08030','ESFP':'#e0a040',
}

def create_mbti_image(mbti_type, nickname):
    W, H = 1000, 600
    color = MBTI_COLORS.get(mbti_type, '#4a5568')
    img = Image.new('RGB', (W, H), color)
    draw = ImageDraw.Draw(img)
    for i in range(H):
        t = i / H
        r, g, b = [int(int(color[1:3],16)*(1-t*0.4)), int(int(color[3:5],16)*(1-t*0.4)), int(int(color[5:7],16)*(1-t*0.4))]
        draw.rectangle([(0, i), (W, i+1)], fill=(r, g, b))
    _tcx(draw, mbti_type, W//2, 120, lf(110, True), '#ffffff')
    desc = MBTI_DESCRIPTIONS.get(mbti_type, {}).get('name', '')
    _tcx(draw, desc, W//2, 250, lf(36, True), '#ffffffcc')
    _tcx(draw, f"@{nickname}", W//2, 490, lf(28, True), '#ffffff99')
    _tcx(draw, "@mbtiuzbot", W//2, 540, lf(20), '#ffffff66')
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=95)
    buf.seek(0)
    return buf

# ============================================================
# START HANDLER
# ============================================================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    cid = message.chat.id
    text = message.text
    clear_sess(cid)
    if 's_' in text:
        parts = text.split('s_')
        if len(parts) > 1:
            test_id = 's_' + parts[1].strip()
            cursor.execute("SELECT creator_name, creator_photo, creator_id FROM tests WHERE test_id=?", (test_id,))
            t = cursor.fetchone()
            if t:
                owner_name, owner_photo, owner_id = t
                if owner_id == cid:
                    _main_menu(cid, message.from_user)
                    return
                friend_name = get_user_name(message.from_user)
                creator_compat_count = COMPAT_QUESTIONS_PREMIUM_COUNT if is_premium(owner_id) else COMPAT_QUESTIONS_FREE_COUNT
                user_sessions[cid] = {
                    'mode': 'answering', 'test_id': test_id, 'step': 0, 'answers': [],
                    'owner_name': owner_name, 'owner_photo': owner_photo, 'friend_name': friend_name,
                    'total_questions': creator_compat_count
                }
                m = InlineKeyboardMarkup(row_width=1)
                m.add(InlineKeyboardButton("✅ Boshlash", callback_data=f"start_quiz_{test_id}"))
                m.add(InlineKeyboardButton("❌ Bekor", callback_data="cancel"))
                bot.send_message(cid,
                    f"😊 Salom, *{friend_name}*!\n\n🌟 *{owner_name}* ning testiga xush kelibsiz!\n\n{creator_compat_count} ta savolga javob bering 👇",
                    reply_markup=m, parse_mode='Markdown')
                return
            else:
                bot.send_message(cid, "❌ Test topilmadi.")
                return
    u = db_get_user(cid)
    if not u:
        set_sess(cid, step='awaiting_nickname')
        bot.send_message(cid,
            "👋 *Salom! @mbtiuzbot ga xush kelibsiz!*\n\n"
            "Bu yerda siz:\n"
            "🎭 MBTI shaxsiyat tipingizni aniqlay\n"
            "👥 Do'stlar bilan o'xshashlikni tekshira\n"
            "💑 Munosabat o'rnata olasiz!\n\n"
            "Boshlash uchun *taxallusingizni* kiriting:\n_(Faqat lotin harflari, raqamlar va _)",
            parse_mode='Markdown')
    else:
        _main_menu(cid, message.from_user)

def _main_menu(cid, user):
    u = db_get_user(cid)
    nick = u['nickname'] if u else get_user_name(user)
    mbti = u['mbti_type'] if u else None
    prem = '⭐ Premium' if u and is_premium(cid) else ''
    m = InlineKeyboardMarkup(row_width=2)
    if not mbti:
        m.add(InlineKeyboardButton("🧠 MBTI test topshirish", callback_data="start_mbti"))
    else:
        m.add(InlineKeyboardButton("🧠 MBTI testni qayta topshirish", callback_data="start_mbti"))
    m.row(
        InlineKeyboardButton("👤 Profilim", callback_data="my_profile"),
        InlineKeyboardButton("👥 Do'stlar", callback_data="my_friends")
    )
    m.row(
        InlineKeyboardButton("🔗 O'xshashlik testi", callback_data="create_test"),
        InlineKeyboardButton("🔍 Qidirish", callback_data="search_user")
    )
    m.add(InlineKeyboardButton("💑 Munosabatlar", callback_data="relationships"))
    if not is_premium(cid):
        m.add(InlineKeyboardButton("⭐ Premium olish", callback_data="premium_info"))
    txt = f"👋 Salom, *{nick}*! {prem}\n\n"
    if mbti:
        txt += f"🎭 MBTI tipingiz: *{mbti}*\n"
    else:
        txt += "❓ MBTI tipingiz aniqlanmagan\n"
    txt += "\nNima qilmoqchisiz?"
    bot.send_message(cid, txt, reply_markup=m, parse_mode='Markdown')

@bot.message_handler(func=lambda m: sess(m.chat.id).get('step') == 'awaiting_nickname')
def handle_nickname(message):
    cid = message.chat.id
    nick = message.text.strip()
    import re
    if not re.match(r'^[A-Za-z0-9_]{3,20}$', nick):
        bot.send_message(cid, "❌ Taxallus 3-20 belgi, faqat lotin harflari, raqamlar va _ bo'lishi kerak. Qayta kiriting:")
        return
    if db_get_by_nick(nick):
        bot.send_message(cid, f"❌ *{nick}* band. Boshqa taxallus kiriting:", parse_mode='Markdown')
        return
    db_upsert_user(cid, nickname=nick)
    clear_sess(cid)
    bot.send_message(cid, f"✅ *{nick}* — taxallusiz saqlandi!\n\nEndi MBTI testni topshirib, shaxsiyat tipingizni aniqlang 👇", parse_mode='Markdown')
    _main_menu(cid, message.from_user)

@bot.message_handler(commands=['test'])
def cmd_test(message):
    cid = message.chat.id
    if not db_get_user(cid):
        bot.send_message(cid, "Avval /start bilan ro'yxatdan o'ting!")
        return
    _begin_mbti(cid)

def _begin_mbti(cid):
    old_session = user_sessions.get(cid)
    if old_session and old_session.get('mode') == 'mbti' and 'quiz_msg_id' in old_session:
        try: bot.delete_message(cid, old_session['quiz_msg_id'])
        except: pass
    clear_sess(cid)
    questions = get_mbti_questions_for_user(cid)
    user_sessions[cid] = {'mode': 'mbti', 'step': 0, 'answers': [], 'total_questions': len(questions)}
    _send_mbti_q(cid)

def _send_mbti_q(cid):
    session = user_sessions.get(cid)
    if not session or session.get('mode') != 'mbti': return
    step = session.get('step', 0)
    total = session.get('total_questions', MBTI_QUESTIONS_FREE_COUNT)
    if step >= total:
        _finish_mbti(cid)
        return
    dic, q, a, b = MBTI_QUESTIONS[step]
    caption = f"🧠 *{step+1}/{total}*\n\n{q}"
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton(a, callback_data="mbti_0"),
               InlineKeyboardButton(b, callback_data="mbti_1"))
    try:
        img = create_question_image(step % len(COMPAT_QUESTIONS))
        if 'quiz_msg_id' in session:
            try:
                bot.edit_message_media(
                    media=InputMediaPhoto(img, caption=caption, parse_mode='Markdown'),
                    chat_id=cid, message_id=session['quiz_msg_id'], reply_markup=markup)
                return
            except: pass
        msg = bot.send_photo(cid, img, caption=caption, reply_markup=markup, parse_mode='Markdown')
        session['quiz_msg_id'] = msg.message_id
    except:
        if 'quiz_msg_id' in session:
            try:
                bot.edit_message_text(caption, cid, session['quiz_msg_id'], reply_markup=markup, parse_mode='Markdown')
                return
            except: pass
        msg = bot.send_message(cid, caption, reply_markup=markup, parse_mode='Markdown')
        session['quiz_msg_id'] = msg.message_id

def _finish_mbti(cid):
    session = user_sessions.get(cid)
    if not session or session.get('mode') != 'mbti': return
    total = session.get('total_questions', MBTI_QUESTIONS_FREE_COUNT)
    if len(session['answers']) != total:
        bot.send_message(cid, "❌ Test to'liq tugamadi. Qayta boshlang: /test")
        if 'quiz_msg_id' in session:
            try: bot.delete_message(cid, session['quiz_msg_id'])
            except: pass
        clear_sess(cid)
        return
    mbti = calculate_mbti(session['answers'])
    db_upsert_user(cid, mbti_type=mbti, mbti_answers=json.dumps(session['answers']))
    if 'quiz_msg_id' in session:
        try: bot.delete_message(cid, session['quiz_msg_id'])
        except: pass
    answers_copy = list(session['answers'])
    clear_sess(cid)
    u = db_get_user(cid)
    img = create_mbti_image(mbti, u['nickname'] if u else 'User')
    desc = MBTI_DESCRIPTIONS.get(mbti, {})
    compat = MBTI_COMPAT.get(mbti, [])
    premium_user = is_premium(cid)
    if premium_user:
        pcts = calculate_mbti_percentages(answers_copy)
        txt = (
            f"🎉 Sizning MBTI tipingiz: *{mbti}* {desc.get('emoji', '')}\n"
            f"*{desc.get('name', '')}*\n\n"
            f"📊 *Shkala foizlari:*\n"
            f"  E {pcts.get('E',50)}% vs I {pcts.get('I',50)}%\n"
            f"  S {pcts.get('S',50)}% vs N {pcts.get('N',50)}%\n"
            f"  T {pcts.get('T',50)}% vs F {pcts.get('F',50)}%\n"
            f"  J {pcts.get('J',50)}% vs P {pcts.get('P',50)}%\n\n"
            f"📖 {desc.get('short', '')}\n\n"
            f"📈 Mos keluvchi tiplar: {', '.join(compat[:3])}"
        )
        m = InlineKeyboardMarkup(row_width=1)
        m.add(InlineKeyboardButton("📋 Batafsil tahlil ko'rish", callback_data=f"mbti_detail_{mbti}"))
        m.add(InlineKeyboardButton("🏠 Bosh menyu", callback_data="main_menu"))
    else:
        txt = (f"🎉 Sizning MBTI tipingiz: *{mbti}* {desc.get('emoji', '')}\n"
               f"*{desc.get('name', '')}*\n\n"
               f"📖 {desc.get('short', '')}\n\n"
               f"📈 Mos keluvchi tiplar: {', '.join(compat[:3])}\n\n"
               f"⭐ *Premium* bilan 50 savollik test va batafsil tahlil!")
        m = InlineKeyboardMarkup(row_width=1)
        m.add(InlineKeyboardButton("⭐ Premium olish", callback_data="premium_info"))
        m.add(InlineKeyboardButton("🏠 Bosh menyu", callback_data="main_menu"))
    try:
        bot.send_photo(cid, img, caption=txt, reply_markup=m, parse_mode='Markdown')
    except:
        bot.send_message(cid, txt, reply_markup=m, parse_mode='Markdown')

@bot.message_handler(commands=['profil'])
def cmd_profil(message):
    cid = message.chat.id
    if not db_get_user(cid):
        bot.send_message(cid, "Avval /start bilan ro'yxatdan o'ting!")
        return
    _show_profile(cid, cid)

def _show_profile(cid, target_id, edit_msg_id=None):
    u = db_get_user(target_id)
    if not u:
        bot.send_message(cid, "❌ Foydalanuvchi topilmadi!")
        return
    own = (cid == target_id)
    desc = MBTI_DESCRIPTIONS.get(u['mbti_type'], {}) if u['mbti_type'] else {}
    partner = get_partner(target_id)
    friends = get_friends(target_id)
    if partner:
        pid = other_id(partner, target_id)
        pu = db_get_user(pid)
        pnick = pu['nickname'] if pu else '?'
        rel_txt = f"{rel_type_emoji(partner[3])} *{partner[3]}*: @{pnick}"
    else:
        rel_txt = "💔 Bo'sh"
    premium_badge = " ⭐" if u['is_premium'] and is_premium(target_id) else ""
    txt = f"{'👤' if own else '🔍'} *{u['nickname']}{premium_badge}*\n\n"
    if u['mbti_type']:
        txt += f"🎭 MBTI: *{u['mbti_type']} {desc.get('emoji', '')}*\n"
        txt += f"🏷 *{desc.get('name', '')}*\n"
    else:
        txt += "🎭 MBTI: *Aniqlanmagan*\n"
    txt += f"\n💑 Holat: {rel_txt}\n"
    txt += f"👥 Do'stlar: {len(friends)} ta\n"
    txt += f"🔓 Profil: {'Ochiq' if u['profile_open'] else 'Yopiq'}"
    m = InlineKeyboardMarkup(row_width=2)
    if own:
        m.add(InlineKeyboardButton("🔒 Profil ko'rinishi", callback_data="toggle_visibility"))
        m.add(InlineKeyboardButton("🏠 Bosh menyu", callback_data="main_menu"))
    else:
        m.add(InlineKeyboardButton("👫 Do'stlik", callback_data=f"send_req_{target_id}_Yaqin do'st"))
        m.add(InlineKeyboardButton("💑 Sevishganlar", callback_data=f"send_req_{target_id}_Sevishganlar"))
        m.add(InlineKeyboardButton("💍 Zaks", callback_data=f"send_req_{target_id}_Zaks"))
    if edit_msg_id:
        try:
            bot.edit_message_text(txt, cid, edit_msg_id, reply_markup=m, parse_mode='Markdown')
            return
        except: pass
    bot.send_message(cid, txt, reply_markup=m, parse_mode='Markdown')

@bot.message_handler(commands=['qidir'])
def cmd_qidir(message):
    cid = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(cid, "Foydalanish: /qidir [taxallus]")
        return
    _search_and_show(cid, parts[1].strip())

def _search_and_show(cid, nick):
    u = db_get_by_nick(nick)
    if not u:
        bot.send_message(cid, f"❌ *{nick}* topilmadi.", parse_mode='Markdown')
        return
    if not u['profile_open'] and u['user_id'] != cid:
        bot.send_message(cid, "🔒 Bu foydalanuvchi profili yopiq.")
        return
    _show_profile(cid, u['user_id'])

@bot.message_handler(commands=['dostlar'])
def cmd_dostlar(message):
    cid = message.chat.id
    if not db_get_user(cid):
        bot.send_message(cid, "Avval /start bilan ro'yxatdan o'ting!")
        return
    friends = get_friends(cid)
    if not friends:
        bot.send_message(cid, "👥 Do'stlar ro'yxati bo'sh.\n\n/taklif [taxallus] Yaqin do'st — do'stlik taklifi yuboring!")
        return
    txt = "👥 *Do'stlaringiz:*\n\n"
    m = InlineKeyboardMarkup(row_width=1)
    for r in friends:
        oid = other_id(r, cid)
        ou = db_get_user(oid)
        if ou:
            mbti = ou['mbti_type'] or '?'
            txt += f"👤 *{ou['nickname']}* — {mbti}\n"
            m.add(InlineKeyboardButton(f"👤 {ou['nickname']}", callback_data=f"view_user_{oid}"))
    bot.send_message(cid, txt, reply_markup=m, parse_mode='Markdown')

@bot.message_handler(commands=['taklif'])
def cmd_taklif(message):
    cid = message.chat.id
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.send_message(cid, "Foydalanish: /taklif [taxallus] [Yaqin do'st | Sevishganlar | Zaks]")
        return
    nick, rel_type = parts[1].strip(), parts[2].strip()
    _send_relationship_request(cid, nick, rel_type)

def _send_relationship_request(from_id, nick, rel_type):
    if rel_type not in ["Yaqin do'st", "Sevishganlar", "Zaks"]:
        bot.send_message(from_id, "❌ Tur noto'g'ri. Turlar: Yaqin do'st | Sevishganlar | Zaks")
        return
    to_u = db_get_by_nick(nick)
    if not to_u:
        bot.send_message(from_id, f"❌ *{nick}* topilmadi.", parse_mode='Markdown')
        return
    to_id = to_u['user_id']
    if to_id == from_id:
        bot.send_message(from_id, "❌ O'zingizga taklif yuborib bo'lmaydi!")
        return
    if not to_u['profile_open']:
        bot.send_message(from_id, "❌ Bu foydalanuvchi profili yopiq.")
        return
    if rel_type in ['Sevishganlar', 'Zaks']:
        if get_partner(from_id):
            bot.send_message(from_id, "❌ Siz allaqachon munosabatdasiz! /ajrash bilan ajrashing.")
            return
        if get_partner(to_id):
            bot.send_message(from_id, f"❌ *{nick}* allaqachon munosabatda.", parse_mode='Markdown')
            return
    cursor.execute(
        "SELECT id FROM relationships WHERE ((from_id=? AND to_id=?) OR (from_id=? AND to_id=?)) AND rel_type=? AND status='active'",
        (from_id, to_id, to_id, from_id, rel_type))
    if cursor.fetchone():
        bot.send_message(from_id, "✅ Siz allaqachon bu odam bilan munosabatdasiz!")
        return
    cursor.execute(
        "SELECT id FROM relationships WHERE from_id=? AND to_id=? AND rel_type=? AND status='pending'",
        (from_id, to_id, rel_type))
    if cursor.fetchone():
        bot.send_message(from_id, "⏳ Taklif allaqachon yuborilgan, javob kutilmoqda.")
        return
    cursor.execute(
        "INSERT INTO relationships(from_id, to_id, rel_type, status, created_at) VALUES(?,?,?,'pending',?)",
        (from_id, to_id, rel_type, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    rel_id = cursor.lastrowid
    from_u = db_get_user(from_id)
    from_nick = from_u['nickname'] if from_u else '?'
    emoji = rel_type_emoji(rel_type)
    m = InlineKeyboardMarkup(row_width=2)
    m.add(InlineKeyboardButton("✅ Qabul qilish", callback_data=f"rel_accept_{rel_id}"),
          InlineKeyboardButton("❌ Rad etish", callback_data=f"rel_reject_{rel_id}"))
    try:
        bot.send_message(to_id,
            f"💌 *{from_nick}* sizga {emoji} *{rel_type}* taklifini yubordi!\n\nQabul qilasizmi?",
            reply_markup=m, parse_mode='Markdown')
        bot.send_message(from_id, f"✅ Taklif *{nick}* ga yuborildi! Javob kutilmoqda ⏳", parse_mode='Markdown')
    except:
        bot.send_message(from_id, "❌ Foydalanuvchiga xabar yuborib bo'lmadi.")

@bot.message_handler(commands=['ajrash'])
def cmd_ajrash(message):
    cid = message.chat.id
    partner = get_partner(cid)
    if not partner:
        bot.send_message(cid, "❌ Siz hech qanday munosabatda emassiz.")
        return
    pid = other_id(partner, cid)
    pu = db_get_user(pid)
    pnick = pu['nickname'] if pu else '?'
    m = InlineKeyboardMarkup(row_width=2)
    m.add(InlineKeyboardButton("✅ Ha, ajrashaman", callback_data=f"confirm_break_{partner[0]}"),
          InlineKeyboardButton("❌ Yo'q", callback_data="cancel"))
    bot.send_message(cid,
        f"⚠️ *{pnick}* bilan {rel_type_emoji(partner[3])} *{partner[3]}* munosabatini bekor qilmoqchimisiz?",
        reply_markup=m, parse_mode='Markdown')

def _compat_send_q(cid, mode):
    session = user_sessions[cid]
    step = session['step']
    total = session.get('total_questions', COMPAT_QUESTIONS_FREE_COUNT)
    q = COMPAT_QUESTIONS[step]
    caption = (f"📝 *{step+1}/{total}*\n{q['text']}" if mode == 'creator'
               else f"📝 *{step+1}/{total}*\n{session['owner_name']} {q['ask_friend']}")
    markup = mk(q['options'], f"ans_{mode}")
    img = create_question_image(step)
    if 'quiz_msg_id' in session:
        try:
            bot.edit_message_media(
                media=InputMediaPhoto(img, caption=caption, parse_mode='Markdown'),
                chat_id=cid, message_id=session['quiz_msg_id'], reply_markup=markup)
            return
        except: pass
    msg = bot.send_photo(cid, img, caption=caption, reply_markup=markup, parse_mode='Markdown')
    session['quiz_msg_id'] = msg.message_id

def _compat_finish_creating(cid):
    session = user_sessions[cid]
    test_id = generate_test_id()
    cursor.execute(
        "INSERT INTO tests(test_id, creator_id, creator_name, creator_photo, answers, created_at) VALUES(?,?,?,?,?,?)",
        (test_id, session['creator_id'], session['creator_name'], None,
         json.dumps(session['answers']), datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    link = f"https://t.me/{bot.get_me().username}?start={test_id}"
    user_sessions[cid] = {'mode': 'awaiting_photo', 'test_id': test_id}
    bot.send_message(cid, "✅", reply_markup=remove_keyboard())
    km = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    km.row(KeyboardButton("🖼 Avatar"), KeyboardButton("⏩ O'tkazib yuborish"))
    km.row(KeyboardButton("🚫 Bekor qilish"))
    bot.send_message(cid,
        f"🎉 *{session['creator_name']}, test tayyor!*\n\n🔗 `{link}`\n\n📢 Do'stlaringizga yuboring!\n\n📸 Profil rasmingizni qo'shing:",
        reply_markup=km, parse_mode='Markdown')

def _compat_finish_test(cid, test_id):
    session = user_sessions[cid]
    cursor.execute("SELECT answers, creator_id FROM tests WHERE test_id=?", (test_id,))
    row = cursor.fetchone()
    if not row:
        bot.send_message(cid, "❌ Test topilmadi!")
        user_sessions.pop(cid, None)
        return
    creator_ans = json.loads(row[0])
    creator_id = row[1]
    friend_ans = session['answers']
    total = session.get('total_questions', COMPAT_QUESTIONS_FREE_COUNT)
    compare_count = min(len(creator_ans), len(friend_ans), total)
    matches = sum(1 for i in range(compare_count) if creator_ans[i] == friend_ans[i])
    percentage = int(matches / compare_count * 100) if compare_count > 0 else 0
    matches_list = []
    for i in range(compare_count):
        if creator_ans[i] == friend_ans[i]:
            matches_list.append(COMPAT_QUESTIONS[i]['options'][creator_ans[i]][:20])
    cursor.execute(
        "INSERT INTO participants(test_id, participant_id, participant_name, answers, similarity, created_at) VALUES(?,?,?,?,?,?)",
        (test_id, cid, session['friend_name'], json.dumps(friend_ans), percentage,
         datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    friend_photo = get_profile_photo(cid)
    if friend_photo:
        cursor.execute("INSERT OR REPLACE INTO user_photos(user_id, photo_file_id) VALUES(?,?)", (cid, friend_photo))
        conn.commit()
    else:
        cursor.execute("SELECT photo_file_id FROM user_photos WHERE user_id=?", (cid,))
        pr = cursor.fetchone()
        friend_photo = pr[0] if pr else None
    cursor.execute("SELECT creator_name, creator_photo FROM tests WHERE test_id=?", (test_id,))
    ow = cursor.fetchone()
    img = create_result_image(percentage, ow[0], session['friend_name'], matches_list, ow[1], friend_photo)
    m = InlineKeyboardMarkup(row_width=1)
    m.add(InlineKeyboardButton("📤 Natijani ulashish", callback_data=f"share_result_{test_id}"))
    m.add(InlineKeyboardButton("✨ O'z testimni yaratish", callback_data="create_test"))
    bot.send_photo(cid, img,
        caption=f"😊 *{session['friend_name']}*, siz *{ow[0]}* bilan *{percentage}%* o'xshaysiz!\n\n✨ O'z testingizni yarating: @{bot.get_me().username}",
        reply_markup=m, parse_mode='Markdown')
    user_sessions.pop(cid, None)

def _show_test_menu(cid, test_id):
    link = f"https://t.me/{bot.get_me().username}?start={test_id}"
    cursor.execute("SELECT creator_name FROM tests WHERE test_id=?", (test_id,))
    row = cursor.fetchone()
    if not row: return
    m = InlineKeyboardMarkup(row_width=2)
    m.add(InlineKeyboardButton("📤 Yuborish", url=f"https://t.me/share/url?url={link}&text=testimiz qanday!"),
          InlineKeyboardButton("📊 Natijalar", callback_data=f"view_test_{test_id}"),
          InlineKeyboardButton("🗑 O'chirish", callback_data=f"delete_test_{test_id}"))
    bot.send_message(cid, f"🎉 *{row[0]}, test tayyor!*\n\n🔗 `{link}`\n\n📢 Havolangizni tarqating!",
                     reply_markup=m, parse_mode='Markdown')

# ============================================================
# PREMIUM QISMI - TO'LIQ TUZATILGAN
# ============================================================

@bot.message_handler(commands=['premium'])
def cmd_premium(message):
    cid = message.chat.id
    if is_premium(cid):
        u = db_get_user(cid)
        bot.send_message(cid, 
            f"⭐ Siz allaqachon *Premium* foydalanuvchisiz!\n\n"
            f"📅 Muddati: *{u['premium_until'] or 'Cheksiz'}*", 
            parse_mode='Markdown')
        return
    _show_premium_info(cid)

def _show_premium_info(cid):
    m = InlineKeyboardMarkup(row_width=1)
    m.add(InlineKeyboardButton(f"⭐ {PREMIUM_PRICE_STARS} Stars bilan to'lash", callback_data="buy_premium"))
    m.add(InlineKeyboardButton("🏠 Orqaga", callback_data="main_menu"))
    txt = (
        f"⭐ *Premium — {PREMIUM_PRICE_STARS} Telegram Stars / {PREMIUM_DAYS} kun*\n\n"
        "⭐️ *Premium imkoniyatlari:*\n\n"
        "🎭 *MBTI Test (Kengaytirilgan):*\n"
        "✅ 50 ta MBTI savoli (oddiy: 24)\n"
        "✅ Har bir shkala bo'yicha foiz ko'rsatkichi\n"
        "✅ MBTI tipingizning batafsil tahlili\n"
        "✅ Sizga eng mos 5 ta kasb tavsiyasi\n\n"
        "🔗 *O'xshashlik testi:*\n"
        "✅ 50 ta savol (oddiy: 24)\n"
        "✅ Har bir toifadagi o'xshashlik foizi\n\n"
        "📊 *Qo'shimcha:*\n"
        "✅ 500+ foydalanuvchi qidirish\n"
        "⭐ Premium nishoni\n\n"
        f"💳 To'lovdan so'ng avtomatik faollashadi!"
    )
    bot.send_message(cid, txt, reply_markup=m, parse_mode='Markdown')

@bot.pre_checkout_query_handler(func=lambda q: True)
def pre_checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    cid = message.chat.id
    
    until = (datetime.now() + timedelta(days=PREMIUM_DAYS)).strftime("%Y-%m-%d")
    
    cursor.execute(
        "UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?",
        (until, cid)
    )
    conn.commit()
    
    try:
        bot.send_message(8321761894,
            f"💳 *Yangi Premium to'lov!*\n"
            f"👤 User ID: `{cid}`\n"
            f"💰 Summa: {PREMIUM_PRICE_STARS} Stars\n"
            f"📅 Muddati: *{until}*\n"
            f"👤 @{message.from_user.username or 'No username'}",
            parse_mode='Markdown')
    except:
        pass
    
    bot.send_message(cid,
        f"✅ *To'lov qabul qilindi!*\n\n"
        f"⭐ Premium {PREMIUM_DAYS} kunga faollashtirildi!\n"
        f"📅 Muddati: *{until}*\n\n"
        f"🎉 Barcha premium imkoniyatlardan foydalanishingiz mumkin!\n\n"
        f"🔄 /start bilan menyuni yangilang",
        parse_mode='Markdown')

@bot.message_handler(content_types=['failed_payment'])
def failed_payment(message):
    bot.send_message(message.chat.id,
        "❌ *To'lov amalga oshmadi!*\n\n"
        "Qayta urinib ko'ring: /premium",
        parse_mode='Markdown')

def _send_stars_invoice(cid):
    try:
        bot.send_invoice(
            chat_id=cid,
            title="⭐ Premium obuna",
            description=f"{PREMIUM_DAYS} kunlik Premium",
            currency="XTR",
            prices=[LabeledPrice("Premium", PREMIUM_PRICE_STARS)],
            provider_token="",
            invoice_payload="premium_subscription",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False
        )
    except Exception as e:
        logging.error(f"Invoice error: {e}")
        bot.send_message(cid, 
            f"❌ To'lovni yuborishda xatolik.\n\n"
            f"Admin bilan bog'lanib premium olishingiz mumkin: {PREMIUM_OWNER}")

# ============================================================
# ADMIN PANEL - STATISTIKA VA BOSHQARUV
# ============================================================

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    cid = message.chat.id
    if cid not in ADMIN_IDS:
        bot.send_message(cid, "❌ Bu komanda faqat adminlar uchun!")
        return
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium=1")
    premium_users = cursor.fetchone()[0]
    
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM users WHERE created_at LIKE ?", (today + '%',))
    today_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE mbti_type IS NOT NULL")
    mbti_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tests")
    total_tests = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM relationships WHERE status='active'")
    total_relationships = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM participants")
    total_participants = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM relationships WHERE status='pending'")
    pending = cursor.fetchone()[0]
    
    txt = (
        f"📊 *Bot statistikasi*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 Umumiy foydalanuvchilar: *{total_users}*\n"
        f"⭐ Premium: *{premium_users}*\n"
        f"📈 Bugun kelgan: *{today_users}*\n"
        f"🎭 MBTI test: *{mbti_users}*\n"
        f"🔗 Testlar: *{total_tests}*\n"
        f"📝 Qatnashchilar: *{total_participants}*\n"
        f"💑 Aktiv munosabatlar: *{total_relationships}*\n"
        f"⏳ Kutilayotgan takliflar: *{pending}*\n"
    )
    
    bot.send_message(cid, txt, parse_mode='Markdown')

@bot.message_handler(commands=['online'])
def cmd_online(message):
    cid = message.chat.id
    if cid not in ADMIN_IDS:
        return
    
    now = datetime.now()
    online = []
    for uid, last in user_last_active.items():
        if (now - last).seconds < 300:
            u = db_get_user(uid)
            if u:
                online.append(f"@{u['nickname']} ({uid})")
    
    txt = f"🟢 *Online foydalanuvchilar:* {len(online)} ta\n\n"
    txt += "\n".join(online[:50]) if online else "Hozir hech kim online emas"
    bot.send_message(cid, txt, parse_mode='Markdown')

@bot.message_handler(commands=['admin'])
def cmd_admin(message):
    cid = message.chat.id
    if cid not in ADMIN_IDS:
        bot.send_message(cid, "❌ Bu komanda faqat adminlar uchun!")
        return
    
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"),
        InlineKeyboardButton("📋 Foydalanuvchilar", callback_data="admin_users"),
        InlineKeyboardButton("⭐ Premium berish", callback_data="admin_give_premium"),
        InlineKeyboardButton("📢 Xabar yuborish", callback_data="admin_broadcast"),
        InlineKeyboardButton("🗑 Tozalash", callback_data="admin_cleanup"),
        InlineKeyboardButton("🟢 Online", callback_data="admin_online")
    )
    bot.send_message(cid, "🔐 *Admin paneli*", reply_markup=m, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith('admin_'))
def admin_callback(call):
    cid = call.message.chat.id
    data = call.data
    
    if cid not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!")
        return
    
    if data == "admin_stats":
        _show_admin_stats(cid, call.message.message_id)
    
    elif data == "admin_users":
        _show_admin_users(cid, call.message.message_id)
    
    elif data == "admin_give_premium":
        bot.send_message(cid, "⭐ Premium berish uchun user ID yoki @username kiriting:")
        set_sess(cid, step='admin_give_premium')
        try: bot.delete_message(cid, call.message.message_id)
        except: pass
    
    elif data == "admin_broadcast":
        bot.send_message(cid, "📢 Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:")
        set_sess(cid, step='admin_broadcast')
        try: bot.delete_message(cid, call.message.message_id)
        except: pass
    
    elif data == "admin_cleanup":
        _admin_cleanup(cid, call.message.message_id)
    
    elif data == "admin_online":
        _show_admin_online(cid, call.message.message_id)

def _show_admin_stats(cid, msg_id=None):
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium=1")
    premium = cursor.fetchone()[0]
    
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM users WHERE created_at LIKE ?", (today + '%',))
    today_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE mbti_type IS NOT NULL")
    mbti_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tests")
    tests = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM participants")
    participants = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM relationships WHERE status='active'")
    relationships = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM relationships WHERE status='pending'")
    pending = cursor.fetchone()[0]
    
    txt = (
        f"📊 *Bot statistikasi*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 Umumiy foydalanuvchilar: *{total}*\n"
        f"⭐ Premium: *{premium}*\n"
        f"📈 Bugun kelgan: *{today_users}*\n"
        f"🎭 MBTI test: *{mbti_users}*\n"
        f"🔗 Testlar: *{tests}*\n"
        f"📝 Qatnashchilar: *{participants}*\n"
        f"💑 Aktiv munosabatlar: *{relationships}*\n"
        f"⏳ Kutilayotgan: *{pending}*\n"
    )
    
    m = InlineKeyboardMarkup(row_width=1)
    m.add(InlineKeyboardButton("🔄 Yangilash", callback_data="admin_stats"))
    m.add(InlineKeyboardButton("◀️ Orqaga", callback_data="admin_back"))
    
    if msg_id:
        try:
            bot.edit_message_text(txt, cid, msg_id, reply_markup=m, parse_mode='Markdown')
            return
        except:
            pass
    
    bot.send_message(cid, txt, reply_markup=m, parse_mode='Markdown')

def _show_admin_users(cid, msg_id=None):
    cursor.execute("SELECT user_id, nickname, mbti_type, is_premium, premium_until, created_at FROM users ORDER BY created_at DESC LIMIT 30")
    users = cursor.fetchall()
    
    txt = "📋 *Oxirgi 30 foydalanuvchi:*\n\n"
    for u in users:
        premium_badge = "⭐" if u[3] else " "
        mbti = u[2] or "❌"
        txt += f"`{u[0]}` {premium_badge} @{u[1]} — {mbti}\n"
    
    txt += f"\n📊 Jami: {len(users)} ta"
    
    m = InlineKeyboardMarkup(row_width=1)
    m.add(InlineKeyboardButton("◀️ Orqaga", callback_data="admin_back"))
    
    if msg_id:
        try:
            bot.edit_message_text(txt, cid, msg_id, reply_markup=m, parse_mode='Markdown')
            return
        except:
            pass
    
    bot.send_message(cid, txt, reply_markup=m, parse_mode='Markdown')

def _admin_cleanup(cid, msg_id=None):
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    cursor.execute("DELETE FROM tests WHERE created_at < ?", (thirty_days_ago,))
    cursor.execute("DELETE FROM participants WHERE created_at < ?", (thirty_days_ago,))
    cursor.execute("DELETE FROM relationships WHERE status='pending' AND created_at < ?", (thirty_days_ago,))
    conn.commit()
    
    txt = "✅ 30 kundan eski testlar va kutilayotgan takliflar o'chirildi!"
    
    m = InlineKeyboardMarkup(row_width=1)
    m.add(InlineKeyboardButton("◀️ Orqaga", callback_data="admin_back"))
    
    if msg_id:
        try:
            bot.edit_message_text(txt, cid, msg_id, reply_markup=m, parse_mode='Markdown')
            return
        except:
            pass
    
    bot.send_message(cid, txt, reply_markup=m, parse_mode='Markdown')

def _show_admin_online(cid, msg_id=None):
    now = datetime.now()
    online = []
    for uid, last in user_last_active.items():
        if (now - last).seconds < 300:
            u = db_get_user(uid)
            if u:
                online.append(f"@{u['nickname']} (`{uid}`)")
    
    txt = f"🟢 *Online foydalanuvchilar:* {len(online)} ta\n\n"
    txt += "\n".join(online[:50]) if online else "Hozir hech kim online emas"
    
    m = InlineKeyboardMarkup(row_width=1)
    m.add(InlineKeyboardButton("🔄 Yangilash", callback_data="admin_online"))
    m.add(InlineKeyboardButton("◀️ Orqaga", callback_data="admin_back"))
    
    if msg_id:
        try:
            bot.edit_message_text(txt, cid, msg_id, reply_markup=m, parse_mode='Markdown')
            return
        except:
            pass
    
    bot.send_message(cid, txt, reply_markup=m, parse_mode='Markdown')

@bot.message_handler(func=lambda m: sess(m.chat.id).get('step') == 'admin_broadcast')
def handle_broadcast(message):
    cid = message.chat.id
    if cid not in ADMIN_IDS:
        return
    
    text = message.text
    clear_sess(cid)
    
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    
    msg = bot.send_message(cid, f"📤 Xabar {len(users)} ta foydalanuvchiga yuborilmoqda...")
    
    sent = 0
    for u in users:
        try:
            bot.send_message(u[0], text, parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            pass
    
    bot.edit_message_text(f"✅ Xabar {sent} ta foydalanuvchiga yuborildi!", cid, msg.message_id)

@bot.message_handler(func=lambda m: sess(m.chat.id).get('step') == 'admin_give_premium')
def handle_give_premium(message):
    cid = message.chat.id
    if cid not in ADMIN_IDS:
        return
    
    text = message.text.strip()
    clear_sess(cid)
    
    if text.startswith('@'):
        u = db_get_by_nick(text[1:])
        if not u:
            bot.send_message(cid, f"❌ {text} topilmadi!")
            return
        user_id = u['user_id']
    else:
        try:
            user_id = int(text)
        except:
            bot.send_message(cid, "❌ Noto'g'ri format! ID yoki @username kiriting.")
            return
    
    until = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    cursor.execute("UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?", (until, user_id))
    conn.commit()
    
    u = db_get_user(user_id)
    bot.send_message(cid, f"✅ *{u['nickname']}* ga 30 kunlik premium berildi!\n📅 Muddati: {until}", parse_mode='Markdown')
    
    try:
        bot.send_message(user_id, 
            f"⭐ Sizga admin tomonidan *Premium* berildi!\n"
            f"📅 Muddati: *{until}*\n\n"
            f"🎉 Barcha premium imkoniyatlardan foydalaning!",
            parse_mode='Markdown')
    except:
        pass

@bot.callback_query_handler(func=lambda c: c.data == 'admin_back')
def admin_back(call):
    cid = call.message.chat.id
    if cid not in ADMIN_IDS:
        return
    try:
        bot.delete_message(cid, call.message.message_id)
    except:
        pass
    cmd_admin(call.message)

# ============================================================
# USER ACTIVITY TRACKING
# ============================================================

@bot.message_handler(func=lambda m: True)
def track_activity(message):
    cid = message.chat.id
    user_last_active[cid] = datetime.now()

# ============================================================
# CALLBACK HANDLER (ASOSIY)
# ============================================================

@bot.callback_query_handler(func=lambda c: True)
def on_cb(call):
    cid = call.message.chat.id
    data = call.data
    bot.answer_callback_query(call.id)

    if data == "main_menu":
        try: bot.delete_message(cid, call.message.message_id)
        except: pass
        _main_menu(cid, call.from_user)
    elif data == "my_profile":
        _show_profile(cid, cid, edit_msg_id=call.message.message_id)
    elif data == "my_friends":
        cmd_dostlar(call.message)
    elif data == "search_user":
        set_sess(cid, step='awaiting_search')
        bot.send_message(cid, "🔍 Qidirish uchun taxallusni kiriting:")
    elif data == "relationships":
        _show_relationships(cid)
    elif data == "start_mbti":
        try: bot.delete_message(cid, call.message.message_id)
        except: pass
        _begin_mbti(cid)
    elif data.startswith("mbti_detail_"):
        mbti_type = data[len("mbti_detail_"):]
        detail_info = MBTI_PREMIUM_DETAILS.get(mbti_type, {})
        detail_txt = detail_info.get('detail', f"*{mbti_type}* haqida batafsil ma'lumot.")
        m = InlineKeyboardMarkup(row_width=1)
        m.add(InlineKeyboardButton("🏠 Bosh menyu", callback_data="main_menu"))
        try: bot.send_message(cid, detail_txt, reply_markup=m, parse_mode='Markdown')
        except: bot.send_message(cid, f"MBTI: {mbti_type}", reply_markup=m)
    elif data.startswith("mbti_"):
        parts_d = data.split("_")
        if len(parts_d) == 2 and parts_d[1].isdigit():
            session = user_sessions.get(cid)
            if not session or session.get('mode') != 'mbti':
                bot.send_message(cid, "❌ Test holati yo'qolgan. /test bilan qayta boshlang.")
                return
            ans = int(parts_d[1])
            session['answers'].append(ans)
            session['step'] = session.get('step', 0) + 1
            _send_mbti_q(cid)
    elif data == "toggle_visibility":
        u = db_get_user(cid)
        new_val = 0 if u['profile_open'] else 1
        db_upsert_user(cid, profile_open=new_val)
        status = "Ochiq 🔓" if new_val else "Yopiq 🔒"
        bot.send_message(cid, f"✅ Profil ko'rinishi: *{status}*", parse_mode='Markdown')
    elif data.startswith("view_user_"):
        tid = int(data.split("_")[2])
        _show_profile(cid, tid)
    elif data == "create_test":
        try: bot.delete_message(cid, call.message.message_id)
        except: pass
        u = db_get_user(cid)
        name = u['nickname'] if u else get_user_name(call.from_user)
        total_q = get_compat_questions_count_for_user(cid)
        user_sessions[cid] = {
            'mode': 'creating', 'step': 0, 'answers': [],
            'creator_name': name, 'creator_id': cid,
            'total_questions': total_q
        }
        km = ReplyKeyboardMarkup(resize_keyboard=True)
        km.add(KeyboardButton("🚫 Bekor qilish"))
        prem_note = " (Premium: 50 savol)" if is_premium(cid) else " (24 savol)"
        bot.send_message(cid, f"❌ Bekor qilish uchun:{prem_note}", reply_markup=km)
        _compat_send_q(cid, 'creator')
    elif data.startswith("start_quiz_"):
        test_id = data[len("start_quiz_"):]
        if cid in user_sessions and user_sessions[cid]['mode'] == 'answering':
            try: bot.delete_message(cid, call.message.message_id)
            except: pass
            _compat_send_q(cid, 'friend')
    elif data.startswith("ans_creator_"):
        if cid not in user_sessions or user_sessions[cid].get('mode') != 'creating': return
        idx = int(data.split("_")[2])
        session = user_sessions[cid]
        total = session.get('total_questions', COMPAT_QUESTIONS_FREE_COUNT)
        session['answers'].append(idx)
        session['step'] += 1
        if session['step'] >= total:
            try: bot.delete_message(cid, session.get('quiz_msg_id'))
            except: pass
            _compat_finish_creating(cid)
        else:
            _compat_send_q(cid, 'creator')
    elif data.startswith("ans_friend_"):
        if cid not in user_sessions or user_sessions[cid].get('mode') != 'answering': return
        idx = int(data.split("_")[2])
        session = user_sessions[cid]
        total = session.get('total_questions', COMPAT_QUESTIONS_FREE_COUNT)
        session['answers'].append(idx)
        session['step'] += 1
        if session['step'] >= total:
            try: bot.delete_message(cid, session.get('quiz_msg_id'))
            except: pass
            _compat_finish_test(cid, session['test_id'])
        else:
            _compat_send_q(cid, 'friend')
    elif data.startswith("share_result_"):
        test_id = data[len("share_result_"):]
        cursor.execute("SELECT similarity, participant_name FROM participants WHERE test_id=? AND participant_id=?", (test_id, cid))
        res = cursor.fetchone()
        if not res: return
        pct, fname = res
        cursor.execute("SELECT creator_name, creator_photo FROM tests WHERE test_id=?", (test_id,))
        t = cursor.fetchone()
        cursor.execute("SELECT photo_file_id FROM user_photos WHERE user_id=?", (cid,))
        pr = cursor.fetchone()
        img = create_result_image(pct, t[0], fname, [], t[1], pr[0] if pr else None)
        bot.send_photo(cid, img, caption=f"😊 *{fname}*, men *{t[0]}* bilan *{pct}%* o'xshayman!\n\n✨ @{bot.get_me().username}", parse_mode='Markdown')
    elif data.startswith("view_test_"):
        test_id = data[len("view_test_"):]
        cursor.execute("SELECT creator_name FROM tests WHERE test_id=?", (test_id,))
        row = cursor.fetchone()
        if not row: return
        cursor.execute("SELECT participant_name, similarity FROM participants WHERE test_id=? ORDER BY similarity DESC", (test_id,))
        parts = cursor.fetchall()
        link = f"https://t.me/{bot.get_me().username}?start={test_id}"
        if not parts:
            txt = f"📊 *{row[0]}*\n\n📋 Hech kim topshirmagan\n\n🔗 `{link}`"
        else:
            txt = f"📊 *{row[0]}*\n\n📋 *Umumiy:* {len(parts)} ta\n\n🏆 *Top do'stlar:*\n"
            for i, (pn, ps) in enumerate(parts[:10], 1):
                txt += f"{i}. {pn} — {ps}%\n"
            txt += f"\n🔗 `{link}`"
        m = InlineKeyboardMarkup(row_width=2)
        m.add(InlineKeyboardButton("📤 Yuborish", url=f"https://t.me/share/url?url={link}&text=Testimni+topshir!"),
              InlineKeyboardButton("🗑 O'chirish", callback_data=f"delete_test_{test_id}"),
              InlineKeyboardButton("◀️ Orqaga", callback_data="main_menu"))
        try: bot.edit_message_text(txt, cid, call.message.message_id, reply_markup=m, parse_mode='Markdown')
        except: bot.send_message(cid, txt, reply_markup=m, parse_mode='Markdown')
    elif data.startswith("delete_test_"):
        test_id = data[len("delete_test_"):]
        cursor.execute("DELETE FROM tests WHERE test_id=? AND creator_id=?", (test_id, cid))
        cursor.execute("DELETE FROM participants WHERE test_id=?", (test_id,))
        conn.commit()
        bot.send_message(cid, "✅ Test o'chirildi!")
        _main_menu(cid, call.from_user)
    elif data.startswith("send_req_"):
        parts = data.split("_")
        target_id = int(parts[2])
        rel_type = " ".join(parts[3:])
        to_u = db_get_user(target_id)
        if to_u:
            _send_relationship_request(cid, to_u['nickname'], rel_type)
    elif data.startswith("rel_accept_"):
        rel_id = int(data.split("_")[2])
        cursor.execute("SELECT * FROM relationships WHERE id=? AND to_id=? AND status='pending'", (rel_id, cid))
        rel = cursor.fetchone()
        if not rel:
            bot.send_message(cid, "❌ Taklif topilmadi.")
            try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
            except: pass
            return
        from_id = rel[1]; rel_type = rel[3]
        if rel_type in ['Sevishganlar', 'Zaks']:
            if get_partner(cid) or get_partner(from_id):
                bot.send_message(cid, "❌ Qabul qilib bo'lmadi — birov allaqachon munosabatda.")
                cursor.execute("DELETE FROM relationships WHERE id=?", (rel_id,))
                conn.commit()
                try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
                except: pass
                return
        cursor.execute("UPDATE relationships SET status='active' WHERE id=?", (rel_id,))
        conn.commit()
        from_u = db_get_user(from_id); to_u = db_get_user(cid)
        emoji = rel_type_emoji(rel_type)
        bot.send_message(cid, f"✅ *{from_u['nickname']}* bilan {emoji} *{rel_type}* boshlandi!", parse_mode='Markdown')
        try: bot.send_message(from_id, f"🎉 *{to_u['nickname']}* taklifingizni qabul qildi! {emoji} *{rel_type}*", parse_mode='Markdown')
        except: pass
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except: pass
    elif data.startswith("rel_reject_"):
        rel_id = int(data.split("_")[2])
        cursor.execute("SELECT from_id, to_id FROM relationships WHERE id=? AND status='pending'", (rel_id,))
        rel = cursor.fetchone()
        if not rel:
            try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
            except: pass
            return
        from_id, to_id = rel
        if to_id != cid: return
        from_nick = db_get_user(from_id)['nickname'] if db_get_user(from_id) else '?'
        cursor.execute("DELETE FROM relationships WHERE id=?", (rel_id,))
        conn.commit()
        bot.send_message(cid, f"❌ *{from_nick}* ning taklifi rad etildi.", parse_mode='Markdown')
        try: bot.send_message(from_id, f"❌ Sizning *{db_get_user(cid)['nickname']}* ga taklifingiz rad etildi!", parse_mode='Markdown')
        except: pass
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except: pass
    elif data.startswith("confirm_break_"):
        rel_id = int(data.split("_")[2])
        cursor.execute("SELECT * FROM relationships WHERE id=? AND status='active' AND (from_id=? OR to_id=?)", (rel_id, cid, cid))
        rel = cursor.fetchone()
        if not rel:
            bot.send_message(cid, "❌ Aktiv munosabat topilmadi.")
            try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
            except: pass
            return
        oid = other_id(rel, cid); rel_type = rel[3]
        cursor.execute("DELETE FROM relationships WHERE id=?", (rel_id,))
        conn.commit()
        emoji = rel_type_emoji(rel_type)
        bot.send_message(cid, f"💔 {emoji} {rel_type} munosabati tugatildi!", parse_mode='Markdown')
        try: bot.send_message(oid, f"💔 *{db_get_user(cid)['nickname']}* siz bilan {rel_type} munosabatini tugatdi.", parse_mode='Markdown')
        except: pass
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except: pass
    elif data == "premium_info":
        _show_premium_info(cid)
    elif data == "buy_premium":
        if is_premium(cid):
            bot.send_message(cid, "⭐ Siz allaqachon Premium foydalanuvchisiz!")
            return
        _send_stars_invoice(cid)
    elif data == "skip_photo":
        if cid in user_sessions and user_sessions[cid].get('mode') == 'awaiting_photo':
            tid = user_sessions.pop(cid)['test_id']
            bot.send_message(cid, "✅ Test tayyor!", reply_markup=remove_keyboard())
            _show_test_menu(cid, tid)
    elif data == "cancel":
        user_sessions.pop(cid, None)
        try: bot.delete_message(cid, call.message.message_id)
        except: pass
        _main_menu(cid, call.from_user)

def _show_relationships(cid):
    partner = get_partner(cid)
    friends = get_friends(cid)
    txt = "💑 *Munosabatlaringiz*\n\n"
    m = InlineKeyboardMarkup(row_width=1)
    if partner:
        oid = other_id(partner, cid)
        ou = db_get_user(oid)
        txt += f"{rel_type_emoji(partner[3])} *{partner[3]}*: *{ou['nickname'] if ou else '?'}*\n\n"
        m.add(InlineKeyboardButton("💔 Ajrashish", callback_data=f"confirm_break_{partner[0]}"))
    else:
        txt += "💔 Hozir munosabatda emassiz\n\n"
    if friends:
        txt += f"👥 *Do'stlar* ({len(friends)} ta):\n"
        for r in friends[:5]:
            oid = other_id(r, cid)
            ou = db_get_user(oid)
            if ou:
                txt += f"  👤 {ou['nickname']}\n"
    txt += "\n/taklif [taxallus] [tur] — yangi taklif yuborish"
    m.add(InlineKeyboardButton("🏠 Bosh menyu", callback_data="main_menu"))
    bot.send_message(cid, txt, reply_markup=m, parse_mode='Markdown')

@bot.message_handler(func=lambda m: sess(m.chat.id).get('step') == 'awaiting_search')
def handle_search(message):
    cid = message.chat.id
    clear_sess(cid)
    _search_and_show(cid, message.text.strip())

@bot.message_handler(func=lambda m: m.text == "🚫 Bekor qilish")
def cancel_h(message):
    cid = message.chat.id
    user_sessions.pop(cid, None)
    bot.send_message(cid, "❌ Bekor qilindi!", reply_markup=remove_keyboard())
    _main_menu(cid, message.from_user)

@bot.message_handler(func=lambda m: m.text == "⏩ O'tkazib yuborish")
def skip_h(message):
    cid = message.chat.id
    if cid in user_sessions and user_sessions[cid].get('mode') == 'awaiting_photo':
        tid = user_sessions.pop(cid)['test_id']
        bot.send_message(cid, "✅ Test tayyor!", reply_markup=remove_keyboard())
        _show_test_menu(cid, tid)

@bot.message_handler(func=lambda m: m.text == "🖼 Avatar")
def avatar_h(message):
    cid = message.chat.id
    if cid in user_sessions and user_sessions[cid].get('mode') == 'awaiting_photo':
        tid = user_sessions[cid]['test_id']
        pid = get_profile_photo(cid)
        if pid:
            cursor.execute("INSERT OR REPLACE INTO user_photos(user_id, photo_file_id) VALUES(?,?)", (cid, pid))
            cursor.execute("UPDATE tests SET creator_photo=? WHERE test_id=?", (pid, tid))
            conn.commit()
            bot.send_message(cid, "✅ Avatar saqlandi!", reply_markup=remove_keyboard())
        else:
            bot.send_message(cid, "❌ Avatar topilmadi!")
        del user_sessions[cid]
        _show_test_menu(cid, tid)

@bot.message_handler(content_types=['photo'])
def photo_h(message):
    cid = message.chat.id
    if cid in user_sessions and user_sessions[cid].get('mode') == 'awaiting_photo':
        pid = message.photo[-1].file_id
        tid = user_sessions.pop(cid)['test_id']
        cursor.execute("INSERT OR REPLACE INTO user_photos(user_id, photo_file_id) VALUES(?,?)", (cid, pid))
        cursor.execute("UPDATE tests SET creator_photo=? WHERE test_id=?", (pid, tid))
        conn.commit()
        bot.send_message(cid, "✅ Rasm saqlandi!", reply_markup=remove_keyboard())
        _show_test_menu(cid, tid)

@bot.message_handler(commands=['yordam'])
def cmd_yordam(message):
    bot.send_message(message.chat.id,
        "📖 *Yordam*\n\n"
        "/start — Botni ishga tushirish\n"
        "/test — MBTI testni boshlash\n"
        "/profil — Profilingizni ko'rish\n"
        "/qidir [taxallus] — Foydalanuvchi qidirish\n"
        "/dostlar — Do'stlar ro'yxati\n"
        "/taklif [taxallus] [tur] — Taklif yuborish\n"
        "   Turlar: Yaqin do'st | Sevishganlar | Zaks\n"
        "/ajrash — Munosabatni bekor qilish\n"
        "/premium — Premium haqida\n"
        "/stats — Statistika (faqat admin)\n"
        "/admin — Admin panel (faqat admin)\n"
        "/online — Online foydalanuvchilar (faqat admin)\n\n"
        "🔗 O'xshashlik testi: oddiy 24, Premium 50 ta savol!\n"
        "🧠 MBTI test: oddiy 24, Premium 50 ta savol!",
        parse_mode='Markdown')

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 @mbtiuzbot is running!", 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def run_bot():
    print("=" * 55)
    print("🤖 @mbtiuzbot — To'liq versiya ishga tushdi!")
    print(f"✅ O'xshashlik testi: {COMPAT_QUESTIONS_FREE_COUNT} (oddiy) / {COMPAT_QUESTIONS_PREMIUM_COUNT} (premium) ta savol")
    print(f"✅ MBTI test: {MBTI_QUESTIONS_FREE_COUNT} (oddiy) / {MBTI_QUESTIONS_PREMIUM_COUNT} (premium) ta savol")
    print("✅ Profil tizimi (nickname, qidirish)")
    print("✅ Munosabatlar (do'st, sevishgan, zaks)")
    print("✅ Premium (Telegram Stars) - avtomatik faollashadi!")
    print("✅ Admin panel - statistika, xabar yuborish, premium berish")
    print("=" * 55)
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            log.error(f"Polling error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_bot()