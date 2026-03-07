import os
import sqlite3
from datetime import datetime
import pandas as pd
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

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
    raise ValueError("BOT_TOKEN tidak ditemukan!")

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

# ================= MENU BUTTON =================
menu_keyboard = [
    ["💰 Uang Masuk", "💸 Uang Keluar"],
    ["📊 Laporan Hari Ini", "📅 Laporan Bulan"],
    ["📆 Laporan Tahun", "📥 Download Excel"],
    ["📈 Grafik Pengeluaran", "♻️ Reset"]
]

reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

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

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 BOT KEUANGAN AKTIF\n\nGunakan menu di bawah.",
        reply_markup=reply_markup
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

    await update.message.reply_text(
        f"💰 Uang masuk {rupiah(jumlah)} berhasil dicatat"
    )

async def keluar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    try:
        jumlah = int(context.args[0])
        ket = " ".join(context.args[1:])
    except:
        await update.message.reply_text("Format salah!\n/keluar 20000 makan")
        return

    tambah_data(user_id, "keluar", jumlah, ket)

    await update.message.reply_text(
        f"💸 Uang keluar {rupiah(jumlah)} berhasil dicatat"
    )

# ================= LAPORAN HARI =================
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

# ================= DOWNLOAD EXCEL =================
async def download_bulan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    data = ambil_data(user_id)

    bulan = datetime.now().strftime("%m")
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

    os.remove(filename)

# ================= GRAFIK =================
async def grafik(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    data = ambil_data(user_id)

    if not data:
        await update.message.reply_text("Belum ada data")
        return

    df = pd.DataFrame(data, columns=["Tipe","Jumlah","Keterangan","Tanggal"])

    df_keluar = df[df["Tipe"] == "keluar"]

    if df_keluar.empty:
        await update.message.reply_text("Belum ada pengeluaran")
        return

    grafik = df_keluar.groupby("Keterangan")["Jumlah"].sum()

    plt.figure()

    grafik.plot(kind="pie", autopct="%1.1f%%")

    plt.title("Grafik Pengeluaran")

    file = f"grafik_{user_id}.png"

    plt.savefig(file)

    plt.close()

    with open(file, "rb") as f:
        await update.message.reply_photo(f)

    os.remove(file)

# ================= RESET =================
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    cursor.execute(
        "DELETE FROM transaksi WHERE user_id=?",
        (user_id,)
    )

    conn.commit()

    await update.message.reply_text("Data berhasil dihapus")

# ================= MENU HANDLER =================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.lower()

    if "uang masuk" in text:
        await update.message.reply_text("Format:\n/masuk 50000 gaji")

    elif "uang keluar" in text:
        await update.message.reply_text("Format:\n/keluar 20000 makan")

    elif "laporan hari" in text:
        await laporan(update, context)

    elif "laporan bulan" in text:
        await bulan(update, context)

    elif "laporan tahun" in text:
        await tahun(update, context)

    elif "download" in text:
        await download_bulan(update, context)

    elif "grafik" in text:
        await grafik(update, context)

    elif "reset" in text:
        await reset(update, context)

# ================= MAIN =================
def run_bot():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("masuk", masuk))
    app.add_handler(CommandHandler("keluar", keluar))
    app.add_handler(CommandHandler("laporan", laporan))
    app.add_handler(CommandHandler("bulan", bulan))
    app.add_handler(CommandHandler("tahun", tahun))
    app.add_handler(CommandHandler("downloadbulan", download_bulan))
    app.add_handler(CommandHandler("reset", reset))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    print("BOT ONLINE 24 JAM...")
    print("Tekan CTRL + C untuk berhenti\n")

    app.run_polling()

# ================= RUN =================
if __name__ == "__main__":
    run_bot()