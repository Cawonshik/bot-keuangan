import os
import sqlite3
from datetime import datetime
import pandas as pd

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

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
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📊 BOT KEUANGAN AKTIF\n\n"
        "/masuk 50000 gaji\n"
        "/keluar 20000 makan\n"
        "/laporan\n"
        "/bulan\n"
        "/tahun\n"
        "/downloadbulan\n"
        "/reset"
    )

def masuk(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        jumlah = int(context.args[0])
        ket = " ".join(context.args[1:])
    except:
        update.message.reply_text("Format salah!\n/masuk 50000 gaji")
        return

    tambah_data(user_id, "masuk", jumlah, ket)
    update.message.reply_text(f"💰 Uang masuk {rupiah(jumlah)} berhasil dicatat")

def keluar(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        jumlah = int(context.args[0])
        ket = " ".join(context.args[1:])
    except:
        update.message.reply_text("Format salah!\n/keluar 20000 makan")
        return

    tambah_data(user_id, "keluar", jumlah, ket)
    update.message.reply_text(f"💸 Uang keluar {rupiah(jumlah)} berhasil dicatat")

def laporan(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    data = ambil_data(user_id)

    if not data:
        update.message.reply_text("Belum ada data")
        return

    hari_ini = datetime.now().strftime("%d-%m-%Y")

    total_masuk = 0
    total_keluar = 0
    text = "📊 LAPORAN HARI INI\n\n"

    for tipe, jumlah, ket, tanggal in data:
        if tanggal == hari_ini:
            emoji = "💰" if tipe == "masuk" else "💸"
            text += f"{emoji} {rupiah(jumlah)} | {ket}\n"

            if tipe == "masuk":
                total_masuk += jumlah
            else:
                total_keluar += jumlah

    saldo = total_masuk - total_keluar

    text += f"\nTotal Masuk: {rupiah(total_masuk)}"
    text += f"\nTotal Keluar: {rupiah(total_keluar)}"
    text += f"\nSaldo: {rupiah(saldo)}"

    update.message.reply_text(text)

# ================= MAIN =================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("masuk", masuk))
    dp.add_handler(CommandHandler("keluar", keluar))
    dp.add_handler(CommandHandler("laporan", laporan))

    print("BOT ONLINE 24 JAM...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()