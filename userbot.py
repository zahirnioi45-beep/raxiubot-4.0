#!/usr/bin/env python3
# Raxi Userbot v4.0 — Full (Termux-ready, hacker-style AFK + spam spinner)
# Save as userbot.py

from telethon import TelegramClient, events
import asyncio, time, datetime, random, platform, psutil, telethon, os, sys
from collections import deque, defaultdict

# ===== CONFIG =====
api_id = int(os.getenv("API_ID") or 22420329)
api_hash = os.getenv("API_HASH") or "d35a8b48fb2747bb12ba804b8952665b"
session_name = os.getenv("SESSION_NAME") or "userbot_session"
OWNER_ID = int(os.getenv("OWNER_ID") or 6347209239)
client = TelegramClient(session_name, api_id, api_hash)
START_TIME = time.time()

# ===== STATE / CACHES =====
afk_status = {"is_afk": False, "reason": "", "since": None}
blacklist = set()
recent_msgs = defaultdict(lambda: deque(maxlen=400))
last_deleted = {}
spam_tasks = {}

# ===== UI HELPERS =====
SPINNER = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
BAR_FILLED = "█"
BAR_EMPTY = "░"

def get_uptime():
    return str(datetime.timedelta(seconds=int(time.time()-START_TIME)))

def is_owner(sid):
    return sid == OWNER_ID

async def spinner_animation(msg, prefix="Processing", cycles=12, delay=0.07):
    try:
        for i in range(cycles):
            frame = SPINNER[i % len(SPINNER)]
            try:
                await msg.edit(f"{prefix}... {frame}")
            except Exception:
                pass
            await asyncio.sleep(delay)
    except Exception:
        pass

def make_progress_bar(percent, length=20):
    try:
        percent = max(0, min(100, percent))
        filled = int(length * percent // 100)
        return BAR_FILLED * filled + BAR_EMPTY * (length - filled)
    except Exception:
        return BAR_EMPTY * length

# ===== EVENT CACHING (for snipe/edit) =====
@client.on(events.NewMessage(outgoing=True))
async def cache_outgoing(event):
    try:
        chat = event.chat_id
        recent_msgs[chat].appendleft({
            "id": event.id,
            "sender": "me",
            "text": getattr(event.message, "message", ""),
            "raw": event.message,
        })
    except Exception:
        pass

@client.on(events.NewMessage(incoming=True))
async def cache_incoming(event):
    try:
        chat = event.chat_id
        recent_msgs[chat].appendleft({
            "id": event.id,
            "sender": getattr(event.sender, "username", None) or getattr(event.sender, "first_name", None) or str(event.sender_id),
            "text": getattr(event.message, "message", ""),
            "raw": event.message,
        })
    except Exception:
        pass

@client.on(events.MessageDeleted())
async def handler_deleted(event):
    try:
        chat = event.chat_id
        deleted_ids = []
        try:
            deleted_ids = list(event.deleted_ids)
        except Exception:
            try:
                if event.deleted_id:
                    deleted_ids = [event.deleted_id]
            except Exception:
                deleted_ids = []
        for did in deleted_ids:
            found = None
            for item in recent_msgs[chat]:
                if item["id"] == did:
                    found = item
                    break
            if found:
                last_deleted[chat] = {
                    "id": found["id"],
                    "sender": found["sender"],
                    "text": found["text"],
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
    except Exception:
        pass

# ===== HELP DATA =====
HELP_SHORT = {
    "system": ("Tampilkan info sistem (CPU/RAM/DISK/uptime).", "`.system`"),
    "alive": ("Cek bot online + uptime.", "`.alive`"),
    "ping": ("Tes respon / latency bot.", "`.ping`"),
    "cpu": ("Tampilkan CPU usage (singkat).", "`.cpu`"),
    "afk": ("Aktifkan AFK. Opsional: alasan.", "`.afk [alasan]`"),
    "unafk": ("Matikan AFK.", "`.unafk`"),
    "snipe": ("Tampilkan pesan terakhir yang dihapus.", "`.snipe`"),
    "purge": ("Hapus banyak pesan (default 10).", "`.purge` atau `.purge 30`"),
    "edit": ("Edit pesan terakhir yang dikirim bot di chat.", "`.edit <teks_baru>`"),
    "tr": ("Terjemahkan teks ke kode bahasa tujuan.", "`.tr en halo`"),
    "reversetext": ("Balik urutan teks.", "`.reversetext halo`"),
    "quote": ("Kirim quote acak.", "`.quote`"),
    "userinfo": ("Ambil info user.", "`.userinfo @nama`"),
    "gcast": ("Broadcast ke semua grup/channel.", "`.gcast Pesan broadcast`"),
    "addbl": ("Tambah id/chat ke blacklist.", "`.addbl <chat_id_or_username>`"),
    "rmbl": ("Hapus id/chat dari blacklist.", "`.rmbl <chat_id_or_username>`"),
    "restart": ("Restart userbot.", "`.restart`"),
    "spam": ("Spam pesan ke chat aktif (owner-only).", "`.spam <jumlah> <delay> <pesan>` atau reply dengan `.spam <jumlah> <delay>`"),
    "spamstop": ("Hentikan spam aktif.", "`.spamstop`"),
}

@client.on(events.NewMessage(pattern=r"^\.help(?: ?(\S+))?"))
async def help_cmd(event):
    if not is_owner(event.sender_id):
        return
    arg = event.pattern_match.group(1)
    if arg:
        key = arg.lower().lstrip(".")
        if key in HELP_SHORT:
            desc, example = HELP_SHORT[key]
            await event.reply(f"📘 **{key}** — {desc}\nContoh: {example}")
        else:
            await event.reply("⚠️ Command tidak dikenal. Ketik `.help` untuk daftar singkat.")
        return
    menu = (
        "```\n"
        "╔════════════════════════╗\n"
        "║    █ R A X I   U S E R B O T █    ║\n"
        "╠════════════════════════╣\n"
        "║ .system   .alive   .ping ║\n"
        "║ .cpu      .afk     .unafk ║\n"
        "║ .snipe    .purge   .edit  ║\n"
        "║ .tr       .reversetext   ║\n"
        "║ .quote    .userinfo .gcast║\n"
        "║ .addbl    .rmbl    .restart║\n"
        "║ .spam     .spamstop       ║\n"
        "╚════════════════════════╝\n"
        "  Raxi v4.0 — Termux Edition\n"
        "```\n"
        "Ketik `.help <command>` untuk panduan singkat."
    )
    msg = await event.reply("> Loading RAXI Help " + SPINNER[0])
    await spinner_animation(msg, prefix="> Loading RAXI Help", cycles=8, delay=0.06)
    await msg.edit(menu)

# ===== PING =====
@client.on(events.NewMessage(pattern=r"^\.ping$"))
async def ping_cmd(event):
    if not is_owner(event.sender_id):
        return
    start = time.time()
    stages = ["⚡ Init...", "💫 Connecting...", "🔎 Measuring...", "🔮 Finalizing..."]
    msg = await event.reply("🏓 Running ping...")
    for s in stages:
        try:
            await asyncio.sleep(0.45)
            await msg.edit(s + " " + SPINNER[random.randint(0, len(SPINNER)-1)])
        except Exception:
            pass
    try:
        t0 = time.time()
        await client.get_me()
        latency = round((time.time() - t0) * 1000, 2)
    except Exception:
        latency = "N/A"
    await msg.edit(f"🏓 Pong!\nLatency: `{latency} ms`\nUptime: {get_uptime()}")

# ===== ALIVE =====
@client.on(events.NewMessage(pattern=r"^\.alive$"))
async def alive_cmd(event):
    if not is_owner(event.sender_id):
        return
    stages = ["Bootloader -> OK", "Kernel -> OK", "Services -> OK", "Interface -> OK", "Userbot -> ONLINE"]
    msg = await event.reply("🌸 Boot sequence initiated...")
    for i, s in enumerate(stages):
        try:
            await msg.edit(f"{s} {SPINNER[i % len(SPINNER)]}")
        except Exception:
            pass
        await asyncio.sleep(0.5)
    me = await client.get_me()
    username = getattr(me, "username", "-")
    await msg.edit(f"✓ Raxi Userbot v4.0 \n👤 @{username}\n🕒 Uptime: {get_uptime()}\n✨ Status: ONLINE")

# ===== SYSTEM =====
@client.on(events.NewMessage(pattern=r"^\.system$"))
async def system_cmd(event):
    if not is_owner(event.sender_id):
        return
    msg = await event.reply("💻 Gathering system stats...")
    await spinner_animation(msg, prefix="💻 Gathering", cycles=8, delay=0.06)
    try:
        try:
            cpu = psutil.cpu_percent(interval=0.2)
            cpu_line = f"CPU  : {cpu:.1f}% [{make_progress_bar(cpu, 20)}]"
        except Exception:
            cpu_line = "CPU  : Tidak tersedia ❌"
        try:
            ram = psutil.virtual_memory().percent
            ram_line = f"RAM  : {ram:.1f}% [{make_progress_bar(ram, 20)}]"
        except Exception:
            ram_line = "RAM  : Tidak tersedia ❌"
        try:
            disk = psutil.disk_usage('/').percent
            disk_line = f"DISK : {disk:.1f}% [{make_progress_bar(disk, 20)}]"
        except Exception:
            disk_line = "DISK : Tidak tersedia ❌"
        try:
            l1, l5, l15 = os.getloadavg()
            load_line = f"LOAD : {l1:.2f} {l5:.2f} {l15:.2f}"
        except Exception:
            load_line = "LOAD : N/A"
        try:
            procs = len(psutil.pids())
            proc_line = f"PROC : {procs} proses"
        except Exception:
            proc_line = "PROC : N/A"

        pyver = platform.python_version()
        telever = getattr(telethon, "__version__", "unknown")
        os_name = platform.system()
        arch = platform.machine()
        uptime = get_uptime()

        pretty = (
            "```\n"
            "╔═══════════════════════════════════╗\n"
            "║        ░ R A X I   S Y S T E M ░  ║\n"
            "╠═══════════════════════════════════╣\n"
            f"{cpu_line}\n"
            f"{ram_line}\n"
            f"{disk_line}\n"
            f"{load_line}\n"
            f"{proc_line}\n"
            "─────────────────────────────────────\n"
            f"Python : {pyver}\n"
            f"Telethon: {telever}\n"
            f"OS : {os_name} ({arch})\n"
            f"Uptime : {uptime}\n"
            "─────────────────────────────────────\n"
            "Mode: Termux Safe\n"
            "```"
        )
        await msg.edit(pretty)
    except Exception as e:
        await msg.edit(f"⚠️ Error .system: `{e}`")

# ===== CPU =====
@client.on(events.NewMessage(pattern=r"^\.cpu$"))
async def cpu_quick(event):
    if not is_owner(event.sender_id): return
    try:
        cpu = psutil.cpu_percent(interval=0.2)
        bar = make_progress_bar(cpu, length=20)
        await event.reply(f"🧠 CPU: {cpu:.1f}% [{bar}]")
    except Exception:
        await event.reply("🧠 CPU: Tidak tersedia ❌")

# ===== HACKER-ULTIMATE AFK / UNAFK (scan + typing + glitch) =====
import string

def glitch_text(text, intensity=0.35):
    symbols = "!@#$%^&*()<>?/{}[]~+="
    out = []
    for ch in text:
        if ch.isspace():
            out.append(ch)
        elif random.random() < intensity:
            out.append(random.choice(symbols))
        else:
            out.append(ch)
    return "".join(out)

async def typing_effect(msg, lines, char_delay=0.03, line_delay=0.18):
    try:
        for line in lines:
            acc = ""
            for ch in line:
                acc += ch
                await msg.edit(acc)
                await asyncio.sleep(char_delay)
            await asyncio.sleep(line_delay)
    except Exception:
        pass

async def scan_effect(msg, frames=None, delay=0.35):
    if frames is None:
        frames = [
            "[•] Initializing modules...",
            "[••] Probing network...",
            "[•••] Scanning process table...",
            "[••••] Hooking user context...",
            "[•••••] AFK PROTOCOL ARMED"
        ]
    try:
        for f in frames:
            await msg.edit(f)
            await asyncio.sleep(delay)
    except Exception:
        pass

async def progress_bar_effect(msg, action="Activating", steps=10, delay=0.18):
    try:
        for i in range(steps + 1):
            pct = int((i / steps) * 100)
            filled = "█" * i
            empty = "░" * (steps - i)
            await msg.edit(f"💻 {action}...\n[{filled}{empty}] {pct}%")
            await asyncio.sleep(delay)
    except Exception:
        pass

@client.on(events.NewMessage(pattern=r"^\.afk(?: (.+))?"))
async def go_afk(event):
    if not is_owner(event.sender_id):
        return
    reason = event.pattern_match.group(1) or "Sedang AFK"
    afk_status["is_afk"] = True
    afk_status["reason"] = reason
    afk_status["since"] = time.time()
    msg = await event.reply("💻 Booting AFK protocol...\n")
    await scan_effect(msg, delay=0.28)
    await typing_effect(msg, [glitch_text("Deploying AFK hooks..."), "Encrypting presence token...", f"Reason: {reason}"], char_delay=0.02)
    await progress_bar_effect(msg, action="Engaging AFK", steps=12, delay=0.12)
    start_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final = (
        "```\n"
        "╔══════════════════════════════╗\n"
        "║     R A X I  A F K  C O N S O L E     ║\n"
        "╠══════════════════════════════╣\n"
        f"║ STATUS :  ACTIVE{' ' * 7}║\n"
        f"║ START  :  {start_ts}     ║\n"
        f"║ REASON :  {reason[:28]:<28} ║\n"
        "╚══════════════════════════════╝\n"
        "```"
    )
    try:
        await msg.edit(final)
    except Exception:
        await msg.edit(f"💤 AFK Aktif — {reason}\nMulai: {start_ts}")

@client.on(events.NewMessage(pattern=r"^\.unafk$"))
async def unafk(event):
    if not is_owner(event.sender_id):
        return
    if not afk_status.get("is_afk"):
        return await event.reply("⚠️ Kamu tidak sedang AFK.")
    dur = int(time.time() - afk_status.get("since", time.time()))
    afk_status["is_afk"] = False
    afk_status["reason"] = ""
    afk_status["since"] = None
    msg = await event.reply("💻 Deactivating AFK protocol...\n")
    for _ in range(2):
        try:
            await msg.edit(glitch_text("Terminating hooks..."))
            await asyncio.sleep(0.22)
            await msg.edit(glitch_text("Clearing presence tokens..."))
            await asyncio.sleep(0.22)
        except Exception:
            pass
    await progress_bar_effect(msg, action="Disengaging", steps=10, delay=0.12)
    try:
        await msg.edit(f"💻 AFK DEACTIVATED\n⏱ Duration: {str(datetime.timedelta(seconds=dur))}\nStatus: [OK]")
    except Exception:
        await msg.edit(f"✅ AFK dimatikan. Durasi: {str(datetime.timedelta(seconds=dur))}")

@client.on(events.NewMessage(outgoing=True))
async def auto_unafk(event):
    if not is_owner(event.sender_id):
        return
    text = getattr(event.message, "message", "") or ""
    ignore_cmds = {".afk", ".unafk", ".help", ".restart", ".ping", ".alive"}
    first = text.strip().split(" ", 1)[0].lower() if text.strip() else ""
    if first in ignore_cmds:
        return
    since = afk_status.get("since")
    if since and (time.time() - since) < 1.0:
        return
    if afk_status.get("is_afk"):
        dur = int(time.time() - afk_status.get("since", time.time()))
        afk_status["is_afk"] = False
        afk_status["reason"] = ""
        afk_status["since"] = None
        msg = await event.reply("💻 Auto Deactivating AFK protocol...\n")
        await scan_effect(msg, frames=[
            "[•] Detecting outgoing activity...",
            "[••] Validating user intent...",
            "[•••] Preparing deactivation..."
        ], delay=0.25)
        try:
            await typing_effect(msg, [glitch_text("Shutting down presence...")], char_delay=0.02)
            await progress_bar_effect(msg, action="Auto-Disengage", steps=8, delay=0.12)
        except Exception:
            pass
        try:
            await msg.edit(f"💻 AFK DEACTIVATED (AUTO)\n⏱ Duration: {str(datetime.timedelta(seconds=dur))}\nStatus: [OK]")
        except Exception:
            await msg.edit(f"✅ AFK auto-dinonaktifkan. Durasi: {str(datetime.timedelta(seconds=dur))}")

@client.on(events.NewMessage())
async def afk_mention_reply(event):
    if afk_status["is_afk"] and event.message.mentioned:
        since = afk_status.get("since")
        since_text = f" (sejak {datetime.datetime.fromtimestamp(since).strftime('%Y-%m-%d %H:%M:%S')})" if since else ""
        try:
            await event.reply(f"√ User sedang AFK{since_text}\nAlasan: {afk_status['reason']}")
        except Exception:
            pass

# ===== SNIPE =====
@client.on(events.NewMessage(pattern=r"^\.snipe$"))
async def snipe_cmd(event):
    if not is_owner(event.sender_id): return
    data = last_deleted.get(event.chat_id)
    if not data:
        await event.reply("⚠️ Tidak ada pesan yang di-snipe di chat ini.")
        return
    await event.reply(f"🕵️ Snipe — From: {data['sender']}\nTime: {data['time']}\nText: {data['text']}")

# ===== PURGE =====
@client.on(events.NewMessage(pattern=r"^\.purge(?: (\d+))?"))
async def purge_cmd(event):
    if not is_owner(event.sender_id): return
    arg = event.pattern_match.group(1)
    n = int(arg) if arg else 10
    msg = await event.reply(f"🧹 Preparing to purge {n} messages...")
    await spinner_animation(msg, prefix="🧹 Purging", cycles=6, delay=0.06)
    deleted = 0
    try:
        async for m in client.iter_messages(event.chat_id, limit=1000):
            if deleted >= n:
                break
            try:
                await m.delete()
                deleted += 1
            except Exception:
                continue
        await msg.edit(f"✅ Purge selesai. Dihapus: {deleted}")
    except Exception as e:
        await msg.edit(f"⚠️ Purge gagal: {e}")

# ===== EDIT =====
@client.on(events.NewMessage(pattern=r"^\.edit (.+)"))
async def edit_cmd(event):
    if not is_owner(event.sender_id): return
    new_text = event.pattern_match.group(1)
    target_id = None
    for item in recent_msgs[event.chat_id]:
        if item["sender"] == "me":
            target_id = item["id"]
            break
    if not target_id:
        await event.reply("⚠️ Tidak menemukan pesan terakhir yang dikirim bot di chat ini.")
        return
    try:
        await client.edit_message(event.chat_id, target_id, new_text)
        await event.reply("✏️ Pesan berhasil diedit.")
    except Exception as e:
        await event.reply(f"⚠️ Gagal edit: {e}")

# ===== TRANSLATE (fallback) =====
try:
    from deep_translator import GoogleTranslator as DeepTranslator
    TRANSLATOR_BACKEND = "deep"
except Exception:
    try:
        from googletrans import Translator as GoogleTrans
        TRANSLATOR_BACKEND = "google"
        TRANSLATOR = GoogleTrans()
    except Exception:
        TRANSLATOR_BACKEND = None

@client.on(events.NewMessage(pattern=r"^\.tr (.+)"))
async def tr_cmd(event):
    if not is_owner(event.sender_id): return
    arg = event.pattern_match.group(1)
    parts = arg.split(" ", 1)
    if len(parts) < 2:
        await event.reply("Gunakan: `.tr <kode_bahasa> <teks>`")
        return
    lang, text = parts[0], parts[1]
    msg = await event.reply("🌐 Translating...")
    await spinner_animation(msg, prefix="🌐 Translating", cycles=5, delay=0.06)
    try:
        if TRANSLATOR_BACKEND == "deep":
            res = DeepTranslator(source="auto", target=lang).translate(text)
        elif TRANSLATOR_BACKEND == "google":
            res = TRANSLATOR.translate(text, dest=lang).text
        else:
            res = "Translator not installed."
        await msg.edit(f"📘 Hasil ({lang}):\n{res}")
    except Exception as e:
        await msg.edit(f"⚠️ Gagal translate: {e}")

# ===== REVERSE TEXT =====
@client.on(events.NewMessage(pattern=r"^\.reversetext (.+)"))
async def reverse_text(event):
    if not is_owner(event.sender_id): return
    txt = event.pattern_match.group(1)
    await event.reply(txt[::-1])

# ===== QUOTE =====
@client.on(events.NewMessage(pattern=r"^\.quote$"))
async def quote_cmd(event):
    if not is_owner(event.sender_id): return
    msg = await event.reply("🌸 Fetching quote...")
    await spinner_animation(msg, prefix="🌸 Loading quote", cycles=4, delay=0.06)
    quotes = [
        ('"Power is not will. It is the phenomenon of physically making things happen."', "— Madara Uchiha"),
        ('"A lesson without pain is meaningless."', "— Edward Elric"),
        ('"If you don’t take risks, you can’t create a future."', "— Monkey D. Luffy"),
        ('"The world isn’t perfect. But it’s there for us trying the best it can…."', "— Roy Mustang"),
        ('"When you give up, your dreams and everything else they’re gone."', "— Ichigo Kurosaki")
    ]
    q, a = random.choice(quotes)
    await msg.edit(f"🌸 {q}\n{a}")

# ===== USERINFO =====
@client.on(events.NewMessage(pattern=r"^\.userinfo(?: (.+))?"))
async def userinfo_cmd(event):
    if not is_owner(event.sender_id): return
    target_q = event.pattern_match.group(1)
    try:
        if target_q:
            ent = await client.get_entity(target_q)
        else:
            ent = await event.get_sender()
        username = getattr(ent, "username", "-")
        name = getattr(ent, "first_name", "-")
        uid = getattr(ent, "id", "-")
        bio = getattr(ent, "about", "-")
        await event.reply(f"👤 {name}\n🆔 {uid}\n🔹 @{username}\n📝 {bio}")
    except Exception as e:
        await event.reply(f"⚠️ Gagal ambil userinfo: {e}")

# ===== GCAST =====
@client.on(events.NewMessage(pattern=r"^\.gcast (.+)"))
async def gcast_cmd(event):
    if not is_owner(event.sender_id): return
    text = event.pattern_match.group(1)
    msg = await event.reply("📢 Collecting dialogs...")
    await spinner_animation(msg, prefix="📢 Preparing", cycles=6, delay=0.06)
    dialogs = await client.get_dialogs()
    targets = [d.entity.id for d in dialogs if d.is_group or d.is_channel]
    total = len(targets)
    if total == 0:
        await msg.edit("⚠️ No groups/channels found.")
        return
    progress = await event.reply(f"📢 Sending broadcast...\n{make_progress_bar(0,20)} 0/{total}")
    sent = 0
    success = 0
    fail = 0
    for t in targets:
        if t in blacklist:
            sent += 1
            continue
        try:
            await client.send_message(t, text)
            success += 1
        except Exception:
            fail += 1
        sent += 1
        try:
            pct = (sent/total)*100
            await progress.edit(f"📢 Sending broadcast...\n[{make_progress_bar(pct,20)}] {sent}/{total}\n✔️ {success} ❌ {fail}")
        except Exception:
            pass
        await asyncio.sleep(0.07)
    try:
        await progress.edit(f"✅ Broadcast finished.\n✔️ {success} ❌ {fail}")
    except Exception:
        pass

# ===== BLACKLIST (add/rm) =====
@client.on(events.NewMessage(pattern=r"^\.addbl(?: (.+))?"))
async def addbl_cmd(event):
    if not is_owner(event.sender_id): return
    t = event.pattern_match.group(1)
    if not t:
        await event.reply("Gunakan: `.addbl <chat_id_or_username>`")
        return
    try:
        ent = await client.get_entity(t)
        tid = getattr(ent, "id", int(t))
        blacklist.add(tid)
        await event.reply(f"✅ `{t}` ditambahkan ke blacklist.")
    except Exception as e:
        await event.reply(f"⚠️ Gagal: {e}")

@client.on(events.NewMessage(pattern=r"^\.rmbl(?: (.+))?"))
async def rmbl_cmd(event):
    if not is_owner(event.sender_id): return
    t = event.pattern_match.group(1)
    if not t:
        await event.reply("Gunakan: `.rmbl <chat_id_or_username>`")
        return
    try:
        ent = await client.get_entity(t)
        tid = getattr(ent, "id", int(t))
        if tid in blacklist:
            blacklist.remove(tid)
            await event.reply(f"✅ `{t}` dihapus dari blacklist.")
        else:
            await event.reply("⚠️ ID tidak ada di blacklist.")
    except Exception as e:
        await event.reply(f"⚠️ Gagal: {e}")

# ===== RESTART =====
@client.on(events.NewMessage(pattern=r"^\.restart$"))
async def restart_cmd(event):
    if not is_owner(event.sender_id): return
    msg = await event.reply("♻️ Restarting...")
    await spinner_animation(msg, prefix="♻️ Restarting", cycles=6, delay=0.08)
    try:
        await client.disconnect()
    except Exception:
        pass
    os.execv(sys.executable, [sys.executable] + sys.argv)

# ===== SPAM with spinner =====
MAX_SPAM = 50
MIN_DELAY = 0.05

async def spam_spinner(progress_msg, idx, sent, total):
    try:
        frame = SPINNER[idx % len(SPINNER)]
        pct = int((sent/total)*100) if total else 0
        bar = make_progress_bar(pct, length=20)
        await progress_msg.edit(f"{frame}  Spamming... [{bar}] {sent}/{total}")
    except Exception:
        pass

@client.on(events.NewMessage(pattern=r"^\.spam(?: |$)(.*)"))
async def spam_cmd(event):
    if not is_owner(event.sender_id): return

    arg = event.pattern_match.group(1).strip()
    if not arg:
        return await event.reply("⚠️ Gunakan: `.spam <count> <delay> <message>`\nContoh: `.spam 10 0.4 Hello` or reply with `.spam 5 0.3`")

    parts = arg.split(" ", 2)
    try:
        count = int(parts[0])
    except Exception:
        return await event.reply("⚠️ Format salah. `count` harus angka. Contoh: `.spam 10 0.5 Hello`")

    delay = 0.5
    message_text = None

    if len(parts) == 1:
        return await event.reply("⚠️ Berikan delay dan/atau pesan. Contoh: `.spam 5 0.3 Halo`")
    elif len(parts) == 2:
        try:
            delay_val = float(parts[1])
            delay = max(MIN_DELAY, delay_val)
            if event.is_reply:
                rep = await event.get_reply_message()
                if rep and getattr(rep, "message", None):
                    message_text = rep.message
                else:
                    return await event.reply("⚠️ Tidak menemukan pesan reply untuk di-spam.")
            else:
                return await event.reply("⚠️ Jika hanya memberi `count` dan `delay`, reply ke pesan yang mau di-spam.")
        except Exception:
            message_text = parts[1]
    else:
        # len == 3
        try:
            delay_val = float(parts[1])
            delay = max(MIN_DELAY, delay_val)
            message_text = parts[2]
        except Exception:
            message_text = parts[1] + " " + parts[2]
            delay = 0.5

    if count <= 0:
        return await event.reply("⚠️ `count` harus > 0.")
    if count > MAX_SPAM:
        return await event.reply(f"⚠️ Maksimum adalah {MAX_SPAM}.")
    if delay < MIN_DELAY:
        delay = MIN_DELAY

    chat_id = event.chat_id
    existing = spam_tasks.get(chat_id)
    if existing and not existing.done():
        return await event.reply("⚠️ Sudah ada proses spam berjalan di chat ini. Gunakan `.spamstop`.")

    progress = await event.reply(f"🚀 Memulai spam: {count}x | delay {delay}s\nStatus: 0/{count}")

    async def do_spam():
        sent = 0
        try:
            for i in range(count):
                task_ref = spam_tasks.get(chat_id)
                if task_ref is None or task_ref.cancelled():
                    break
                try:
                    await client.send_message(chat_id, message_text)
                    sent += 1
                except Exception:
                    pass
                await spam_spinner(progress, i, sent, count)
                await asyncio.sleep(delay)
        finally:
            spam_tasks.pop(chat_id, None)
            try:
                await progress.edit(f"✅ Spam selesai. Terkirim: {sent}/{count}")
            except Exception:
                pass

    task = asyncio.create_task(do_spam())
    spam_tasks[chat_id] = task

@client.on(events.NewMessage(pattern=r"^\.spamstop$"))
async def spamstop_cmd(event):
    if not is_owner(event.sender_id): return
    chat_id = event.chat_id
    task = spam_tasks.pop(chat_id, None)
    if task:
        task.cancel()
        await event.reply("🛑 Spam dihentikan.")
    else:
        await event.reply("⚠️ Tidak ada spam aktif di chat ini.")

# ===== START =====
if __name__ == "__main__":
    print("🔮 Raxi Userbot v4.0 (Termux Full) — Starting...")
    client.start()
    client.run_until_disconnected()
