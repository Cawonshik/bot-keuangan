import os
import sqlite3
from datetime import datetime
import pandas as pd
import asyncio
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= LOG =================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")

print("STARTING BOT...")
print("TOKEN:", TOKEN)

if not TOKEN:
    raise ValueError("BOT_TOKEN tidak ditemukan di ENV!")

# ================= DATABASE =================
conn = sqlite3.connect("keuangan.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    tipe TEXT,
    jumlah INTEGER,
    keterangan TEXT,
    tanggal TEXT
)
""")
conn.commit()

# ================= HELPER =================
def rupiah(n):
    return f"Rp {n:,.0f}".replace(",", ".")

def tambah_data(user_id, tipe, jumlah, ket):
    tanggal = datetime.now().strftime("%d-%m-%Y")

    cursor.execute("""
    INSERT INTO transaksi (user_id, tipe, jumlah, keterangan, tanggal)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, tipe, jumlah, ket, tanggal))

    conn.commit()

def ambil_data(user_id):
    cursor.execute("""
    SELECT tipe, jumlah, keterangan, tanggal 
    FROM transaksi WHERE user_id=?
    """, (user_id,))
    return cursor.fetchall()

# ================= COMMAND =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 BOT KEUANGAN AKTIF\n\n"
        "Perintah:\n"
        "/masuk 50000 gaji\n"
        "/keluar 20000 makan\n"
        "/laporan\n"
        "/bulan\n"
        "/tahun\n"
        "/downloadbulan\n"
        "/reset"
    )

# ================= INPUT =================
async def masuk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        jumlah = int(context.args[0])
        ket = " ".join(context.args[1:])
    except:
        await update.message.reply_text("Format salah!\n/masuk 50000 gaji")
        return

    tambah_data(user_id, "masuk", jumlah, ket)
    await update.message.reply_text(f"💰 Uang masuk {rupiah(jumlah)} berhasil dicatat")

async def keluar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        jumlah = int(context.args[0])
        ket = " ".join(context.args[1:])
    except:
        await update.message.reply_text("Format salah!\n/keluar 20000 makan")
        return

    tambah_data(user_id, "keluar", jumlah, ket)
    await update.message.reply_text(f"💸 Uang keluar {rupiah(jumlah)} berhasil dicatat")

# ================= LAPORAN =================
async def laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = ambil_data(user_id)

    if not data:
        await update.message.reply_text("Belum ada data")
        return

    hari_ini = datetime.now().strftime("%d-%m-%Y")

    total_masuk = 0
    total_keluar = 0
    text = "📊 LAPORAN HARI INI\n\n"

    for tipe, jumlah, ket, tanggal in data:
        if tanggal == hari_ini:
            emoji = "💰" if tipe == "masuk" else "💸"
            text += f"{emoji} {rupiah(jumlah)} | {ket} | {tanggal}\n"

            if tipe == "masuk":
                total_masuk += jumlah
            else:
                total_keluar += jumlah

    saldo = total_masuk - total_keluar

    text += f"\nTotal Masuk: {rupiah(total_masuk)}"
    text += f"\nTotal Keluar: {rupiah(total_keluar)}"
    text += f"\nSaldo: {rupiah(saldo)}"

    await update.message.reply_text(text)

# ================= BULAN =================
async def bulan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = ambil_data(user_id)

    bulan_now = datetime.now().strftime("%m")
    tahun = datetime.now().strftime("%Y")

    total_masuk = 0
    total_keluar = 0

    for tipe, jumlah, ket, tanggal in data:
        if bulan_now in tanggal and tahun in tanggal:
            if tipe == "masuk":
                total_masuk += jumlah
            else:
                total_keluar += jumlah

    saldo = total_masuk - total_keluar

    await update.message.reply_text(
        f"📅 LAPORAN BULAN INI\n\n"
        f"Total Masuk: {rupiah(total_masuk)}\n"
        f"Total Keluar: {rupiah(total_keluar)}\n"
        f"Saldo: {rupiah(saldo)}"
    )

# ================= TAHUN =================
async def tahun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = ambil_data(user_id)

    tahun_now = datetime.now().strftime("%Y")

    total_masuk = 0
    total_keluar = 0

    for tipe, jumlah, ket, tanggal in data:
        if tahun_now in tanggal:
            if tipe == "masuk":
                total_masuk += jumlah
            else:
                total_keluar += jumlah

    saldo = total_masuk - total_keluar

    await update.message.reply_text(
        f"📆 LAPORAN TAHUN INI\n\n"
        f"Total Masuk: {rupiah(total_masuk)}\n"
        f"Total Keluar: {rupiah(total_keluar)}\n"
        f"Saldo: {rupiah(saldo)}"
    )

# ================= DOWNLOAD =================
bulan_map = {
    "januari": "01","februari": "02","maret": "03","april": "04",
    "mei": "05","juni": "06","juli": "07","agustus": "08",
    "september": "09","oktober": "10","november": "11","desember": "12"
}

async def download_bulan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = ambil_data(user_id)

    bulan = bulan_map.get(context.args[0].lower()) if context.args else datetime.now().strftime("%m")
    tahun = datetime.now().strftime("%Y")

    filtered = []

    for tipe, jumlah, ket, tanggal in data:
        if bulan in tanggal and tahun in tanggal:
            filtered.append([tipe, jumlah, ket, tanggal])

    if not filtered:
        await update.message.reply_text("Tidak ada data bulan ini")
        return

    df = pd.DataFrame(filtered, columns=["Tipe","Jumlah","Keterangan","Tanggal"])

    filename = f"laporan_{user_id}_{bulan}.xlsx"
    df.to_excel(filename, index=False)

    with open(filename, "rb") as f:
        await update.message.reply_document(f)

    try:
        os.remove(filename)
    except:
        pass

# ================= RESET =================
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("DELETE FROM transaksi WHERE user_id=?", (user_id,))
    conn.commit()

    await update.message.reply_text("Data berhasil dihapus")

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("masuk", masuk))
    app.add_handler(CommandHandler("keluar", keluar))
    app.add_handler(CommandHandler("laporan", laporan))
    app.add_handler(CommandHandler("bulan", bulan))
    app.add_handler(CommandHandler("tahun", tahun))
    app.add_handler(CommandHandler("downloadbulan", download_bulan))
    app.add_handler(CommandHandler("reset", reset))

    print("BOT ONLINE 24 JAM...")
    await app.run_polling()

# ================= AUTO RESTART =================
if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            print("ERROR:", e)