import os
import re
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

def tg_send(chat_id: int, text: str):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=15)
    r.raise_for_status()
    return r.json()

@app.route("/api", methods=["GET"])
def health():
    # هذا يفيدك تفتح الرابط بالمتصفح وتتأكد أنه ماكو Crash
    return jsonify({"ok": True, "service": "shazam-charts-bot"})

def parse_shazam_top200(url: str, limit: int = 10):
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # طريقة بسيطة تعتمد على النص الظاهر بالصفحة: رقم ثم عنوان ثم فنان
    lines = [x for x in soup.get_text("\n", strip=True).split("\n") if x]
    out = []
    i = 0
    while i < len(lines) - 2 and len(out) < limit:
        if re.fullmatch(r"\d{1,3}", lines[i]):
            rank = int(lines[i])
            title = lines[i + 1]
            artist = lines[i + 2]
            # فلترة خفيفة
            if len(title) < 80 and len(artist) < 80:
                out.append((rank, title, artist))
            i += 3
        else:
            i += 1
    return out[:limit]

def fmt(items):
    if not items:
        return "ما حصلت بيانات حالياً."
    return "\n".join([f"{r}. {t} — {a}" for r, t, a in items])

@app.route("/api", methods=["POST"])
def webhook():
    if not BOT_TOKEN:
        return jsonify({"ok": False, "error": "BOT_TOKEN not set"}), 500

    update = request.get_json(force=True) or {}
    msg = update.get("message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    text = (msg.get("text") or "").strip()

    if not chat_id:
        return jsonify({"status": "ok"})

    if text.startswith("/start"):
        tg_send(chat_id, "أهلاً! أوامر البوت:\n/world [عدد]\n/top <country-slug> [عدد]\nمثال: /top united-states 10")
        return jsonify({"status": "ok"})

    if text.startswith("/world"):
        parts = text.split()
        limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
        items = parse_shazam_top200("https://www.shazam.com/charts/top-200/world", limit)
        tg_send(chat_id, f"🌍 Global Top {limit}\n\n{fmt(items)}")
        return jsonify({"status": "ok"})

    if text.startswith("/top"):
        parts = text.split()
        country = parts[1] if len(parts) > 1 else "united-states"
        limit = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 10
        url = f"https://www.shazam.com/charts/top-200/{country}"
        items = parse_shazam_top200(url, limit)
        tg_send(chat_id, f"📍 Top {limit} — {country}\n\n{fmt(items)}")
        return jsonify({"status": "ok"})

    tg_send(chat_id, "اكتب /start للشرح.")
    return jsonify({"status": "ok"})
