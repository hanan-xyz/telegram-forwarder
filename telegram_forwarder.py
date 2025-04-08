import logging
import os
from getpass import getpass
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Muat variabel dari file .env
load_dotenv()

# Konfigurasi logging
logging.basicConfig(
    filename='telegram_forwarder.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ambil konfigurasi dari .env
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
PHONE = os.getenv('TELEGRAM_PHONE')
SOURCE_CHANNELS = os.getenv('SOURCE_CHANNELS').split(',')  # Ubah jadi list
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL')
KEYWORDS = os.getenv('KEYWORDS').split(',')  # Ubah jadi list

# Validasi konfigurasi
if not all([API_ID, API_HASH, PHONE, SOURCE_CHANNELS, TARGET_CHANNEL, KEYWORDS]):
    raise ValueError("Pastikan semua variabel di .env telah diisi!")

# Inisialisasi client Telegram
client = TelegramClient('telegram_session', API_ID, API_HASH)

# Fungsi untuk memeriksa kata kunci dalam pesan
def contains_keyword(text, keywords):
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)

# Fungsi untuk login
async def login():
    try:
        await client.start(phone=PHONE)
        if not await client.is_user_authorized():
            logger.info("Memulai proses login...")
            await client.send_code_request(PHONE)
            code = getpass("Masukkan kode verifikasi yang diterima: ")
            try:
                await client.sign_in(PHONE, code)
            except SessionPasswordNeededError:
                password = getpass("Masukkan kata sandi 2FA Anda: ")
                await client.sign_in(password=password)
        logger.info("Login berhasil!")
    except Exception as e:
        logger.error(f"Gagal login: {str(e)}")
        raise

# Event handler untuk pesan baru
@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def forward_message(event):
    try:
        message = event.message
        if message.text and contains_keyword(message.text, KEYWORDS):
            logger.info(f"Pesan dari {event.chat.username or event.chat.id} mengandung kata kunci: {message.id}")
            await client.forward_messages(TARGET_CHANNEL, message)
            logger.info(f"Pesan {message.id} berhasil diteruskan ke {TARGET_CHANNEL}")
    except FloodWaitError as e:
        logger.warning(f"Terkena flood wait, menunggu {e.seconds} detik")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logger.error(f"Gagal meneruskan pesan {message.id}: {str(e)}")

# Fungsi utama
async def main():
    try:
        await login()
        logger.info(f"Client berjalan, memantau {', '.join(SOURCE_CHANNELS)}...")
        print(f"Skrip berjalan pada {datetime.now()}. Cek telegram_forwarder.log untuk detail.")
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Error di fungsi utama: {str(e)}")
        print(f"Terjadi error, cek log untuk detail: {str(e)}")

# Jalankan skrip
if __name__ == "__main__":
    try:
        with client:
            client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Skrip dihentikan oleh pengguna")
        print("Skrip dihentikan dengan Ctrl+C")
    except Exception as e:
        logger.error(f"Error tak terduga: {str(e)}")
        print(f"Error tak terduga, cek log: {str(e)}")
