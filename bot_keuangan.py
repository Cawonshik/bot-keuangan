import os
import sqlite3
from datetime import datetime
import pandas as pd
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fpdf import FPDF

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
    kategori TEXT,
    keterangan TEXT,
    tanggal TEXT
)
""")
conn.commit()

# ================= MENU BUTTON =================
menu_keyboard = [
    ["💰 Uang Masuk", "💸 Uang Keluar"],
    ["📊 Laporan Hari Ini", "📅 Laporan Bulan"],
    ["📈 Grafik Bulanan", "📊 Statistik"],
    ["📥 Export Excel", "📄 Export PDF"],
    ["♻️ Reset"]
]

reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

# ================= HELPER =================
def rupiah(n):
    return f"Rp {n:,.0f}".replace(",", ".")

def tambah_data(user_id, tipe, jumlah, kategori, ket):
    tanggal = datetime.now().strftime("%d-%m-%Y")

    cursor.execute("""
    INSERT INTO transaksi (user_id, tipe, jumlah, kategori, keterangan, tanggal)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, tipe, jumlah, kategori, ket, tanggal))

    conn.commit()

def ambil_data(user_id):
    cursor.execute("""
    SELECT tipe, jumlah, kategori, keterangan, tanggal
    FROM transaksi WHERE user_id=?
    """, (user_id,))
    return cursor.fetchall()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 BOT KEUANGAN PRO\n\nGunakan menu di bawah.",
        reply_markup=reply_markup
    )

# ================= INPUT =================
async def masuk(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    try:
        jumlah = int(context.args[0])
        kategori = context.args[1]
        ket = " ".join(context.args[2:])
    except:
        await update.message.reply_text("Format:\n/masuk 50000 gaji bonus")
        return

    tambah_data(user_id,"masuk",jumlah,kategori,ket)

    await update.message.reply_text(
        f"💰 Uang masuk {rupiah(jumlah)} berhasil dicatat"
    )

async def keluar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    try:
        jumlah = int(context.args[0])
        kategori = context.args[1]
        ket = " ".join(context.args[2:])
    except:
        await update.message.reply_text("Format:\n/keluar 20000 makan nasi")
        return

    tambah_data(user_id,"keluar",jumlah,kategori,ket)

    await update.message.reply_text(
        f"💸 Uang keluar {rupiah(jumlah)} berhasil dicatat"
    )

# ================= LAPORAN HARI =================
async def laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    data = ambil_data(user_id)

    hari_ini = datetime.now().strftime("%d-%m-%Y")

    masuk = 0
    keluar = 0

    text = "📊 LAPORAN HARI INI\n\n"

    for tipe,jumlah,kategori,ket,tanggal in data:

        if tanggal == hari_ini:

            emoji="💰" if tipe=="masuk" else "💸"

            text+=f"{emoji} {rupiah(jumlah)} | {kategori} | {ket}\n"

            if tipe=="masuk":
                masuk+=jumlah
            else:
                keluar+=jumlah

    saldo = masuk - keluar

    text+=f"\nMasuk: {rupiah(masuk)}"
    text+=f"\nKeluar: {rupiah(keluar)}"
    text+=f"\nSaldo: {rupiah(saldo)}"

    await update.message.reply_text(text)

# ================= GRAFIK BULAN =================
async def grafik(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    data = ambil_data(user_id)

    if not data:
        await update.message.reply_text("Belum ada data")
        return

    df = pd.DataFrame(data,columns=["Tipe","Jumlah","Kategori","Ket","Tanggal"])

    df_keluar = df[df["Tipe"]=="keluar"]

    grafik = df_keluar.groupby("Kategori")["Jumlah"].sum()

    plt.figure()
    grafik.plot(kind="pie",autopct="%1.1f%%")

    plt.title("Grafik Pengeluaran")

    file=f"grafik_{user_id}.png"

    plt.savefig(file)
    plt.close()

    await update.message.reply_photo(open(file,"rb"))

    os.remove(file)

# ================= STATISTIK =================
async def statistik(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    data = ambil_data(user_id)

    df = pd.DataFrame(data,columns=["Tipe","Jumlah","Kategori","Ket","Tanggal"])

    df_keluar=df[df["Tipe"]=="keluar"]

    stat=df_keluar.groupby("Kategori")["Jumlah"].sum()

    text="📊 Statistik Pengeluaran\n\n"

    for k,v in stat.items():
        text+=f"{k} : {rupiah(v)}\n"

    await update.message.reply_text(text)

# ================= EXPORT EXCEL =================
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    data = ambil_data(user_id)

    df=pd.DataFrame(data,columns=["Tipe","Jumlah","Kategori","Keterangan","Tanggal"])

    file=f"laporan_{user_id}.xlsx"

    df.to_excel(file,index=False)

    await update.message.reply_document(open(file,"rb"))

    os.remove(file)

# ================= EXPORT PDF =================
async def export_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    data = ambil_data(user_id)

    pdf=FPDF()
    pdf.add_page()

    pdf.set_font("Arial",size=12)

    pdf.cell(0,10,"Laporan Keuangan",ln=True)

    for tipe,jumlah,kategori,ket,tanggal in data:

        line=f"{tanggal} | {tipe} | {kategori} | {jumlah}"

        pdf.cell(0,10,line,ln=True)

    file=f"laporan_{user_id}.pdf"

    pdf.output(file)

    await update.message.reply_document(open(file,"rb"))

    os.remove(file)

# ================= RESET =================
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    cursor.execute("DELETE FROM transaksi WHERE user_id=?", (user_id,))
    conn.commit()

    await update.message.reply_text("Data berhasil dihapus")

# ================= MENU HANDLER =================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.lower()

    if "laporan hari" in text:
        await laporan(update, context)

    elif "grafik" in text:
        await grafik(update, context)

    elif "statistik" in text:
        await statistik(update, context)

    elif "excel" in text:
        await export_excel(update, context)

    elif "pdf" in text:
        await export_pdf(update, context)

    elif "reset" in text:
        await reset(update, context)

    elif "uang masuk" in text:
        await update.message.reply_text("Format:\n/masuk 50000 gaji bonus")

    elif "uang keluar" in text:
        await update.message.reply_text("Format:\n/keluar 20000 makan nasi")

# ================= MAIN =================
def run_bot():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("masuk", masuk))
    app.add_handler(CommandHandler("keluar", keluar))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    print("BOT ONLINE 24 JAM...")

    app.run_polling()

# ================= RUN =================
if __name__ == "__main__":
    run_bot()