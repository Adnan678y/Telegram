import json
import subprocess
import os
import telebot
import time
from telebot.types import Message
from tqdm import tqdm

# 🔹 Telegram Bot Token & Chat ID
BOT_TOKEN = "7684671068:AAHuH9QUe6f8oeOfmNvmf_K-Zj7HeBCDETw"  # Replace with your bot token
CHAT_ID = "1366000165"  # Replace with your chat ID
bot = telebot.TeleBot(BOT_TOKEN)

# 🔹 Paths
json_path = os.path.join(os.path.expanduser("~"), "Downloads", "uploaded.json")
db_path = os.path.join(os.path.expanduser("~"), "Downloads", "upload_log.json")  # Log of uploaded files
download_path = os.path.join(os.path.expanduser("~"), "Downloads")

# 🔹 Ensure directories exist
os.makedirs(download_path, exist_ok=True)

# 🔹 Load or create upload log database
if not os.path.exists(db_path):
    with open(db_path, "w") as db_file:
        json.dump({"uploaded": []}, db_file)

# 🔹 Load uploaded episodes log
def load_uploaded_log():
    with open(db_path, "r") as db_file:
        return json.load(db_file)

# 🔹 Save uploaded episodes log
def save_uploaded_log(data):
    with open(db_path, "w") as db_file:
        json.dump(data, db_file, indent=4)

# 🔹 Function to download an M3U8 file
def download_m3u8(m3u8_link, file_name):
    output_file = os.path.join(download_path, f"{file_name}.mp3")

    try:
        bot.send_message(CHAT_ID, f"📥 Downloading: {file_name}...")

        start_time = time.time()
        command = ["ffmpeg", "-i", m3u8_link, "-c:a", "libmp3lame", output_file]
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        end_time = time.time()
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # Convert to MB
        download_speed = file_size / (end_time - start_time)

        bot.send_message(CHAT_ID, f"✅ Downloaded {file_name} ({file_size:.2f} MB) in {end_time - start_time:.2f} sec ({download_speed:.2f} MB/s)")
        return output_file
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error downloading {file_name}: {e}")
        return None

# 🔹 Function to upload audio to Telegram
def upload_audio(file_path, title, caption=None, retries=3):
    for attempt in range(retries):
        try:
            bot.send_message(CHAT_ID, f"📤 Uploading: {title} (Attempt {attempt + 1}/{retries})...")

            with open(file_path, "rb") as audio:
                bot.send_audio(CHAT_ID, audio, title=title, caption=caption)

            bot.send_message(CHAT_ID, f"✅ Uploaded {title}.")
            return True
        except Exception as e:
            bot.send_message(CHAT_ID, f"❌ Error uploading {title}: {e}. Retrying...")
            time.sleep(5)  # Wait before retry

    bot.send_message(CHAT_ID, f"❌ Upload failed after {retries} attempts.")
    return False

# 🔹 Function to delete a file
def delete_file(file_path):
    try:
        os.remove(file_path)
        print(f"🗑️ Deleted {file_path}.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error deleting file: {e}")

# 🔹 Process episodes sequentially
def process_episodes_sequentially(data):
    uploaded_log = load_uploaded_log()

    for episode in data["Episodes"]:
        name = episode["Name"]
        episode_number = episode["Episode"]

        # Skip if already uploaded
        if name in uploaded_log["uploaded"]:
            bot.send_message(CHAT_ID, f"⚠️ Skipping {name}, already uploaded.")
            continue

        file_path = download_m3u8(episode["Link"], name)
        if file_path:
            title = f"{name} @onlyeightfm"
            caption = f"{name} - Episode {episode_number} @onlyeightfm"

            if upload_audio(file_path, title, caption):
                delete_file(file_path)
                uploaded_log["uploaded"].append(name)  # Log uploaded episode
                save_uploaded_log(uploaded_log)  # Save log

        time.sleep(2)  # Prevent API rate limits

    bot.send_message(CHAT_ID, "✅ All episodes processed successfully!")

# 🔹 Handle JSON file upload
@bot.message_handler(content_types=['document'])
def handle_json_upload(message: Message):
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    with open(json_path, "wb") as json_file:
        json_file.write(downloaded_file)

    bot.reply_to(message, "✅ JSON file received! Processing episodes...")

    with open(json_path, "r") as file:
        data = json.load(file)

    process_episodes_sequentially(data)

# 🔹 Handle /down command
@bot.message_handler(commands=['down'])
def handle_down_command(message: Message):
    try:
        args = message.text.split(" ", 2)
        if len(args) < 3:
            bot.reply_to(message, "❌ Usage: /down <M3U8 Link> <Name>")
            return

        m3u8_link = args[1]
        file_name = args[2]

        bot.reply_to(message, f"🔄 Processing: {file_name}...")
        file_path = download_m3u8(m3u8_link, file_name)

        if file_path:
            upload_audio(file_path, title=file_name)
            delete_file(file_path)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# 🔹 Handle Commands
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🤖 Bot started! Send a JSON file to begin processing.")

@bot.message_handler(commands=['status'])
def status(message):
    uploaded_log = load_uploaded_log()
    count = len(uploaded_log["uploaded"])
    bot.reply_to(message, f"📊 {count} episodes uploaded so far.")

@bot.message_handler(commands=['stop'])
def stop(message):
    bot.reply_to(message, "⛔ Stopping bot...")
    exit(0)

# 🔹 Start the bot
print("🤖 Bot is running...")
bot.send_message(CHAT_ID, "🤖 Bot started! Send a JSON file or use /down <M3U8 Link> <Name>")
bot.polling()
