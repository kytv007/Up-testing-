from pyrogram import Client, filters
import os
import requests
import math

# Replace with your Telegram API credentials
API_ID = "your_api_id"
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"

# Create a Pyrogram client instance
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Download a file from a URL
async def download_file(url, file_name):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024  # 1 KB
    progress = 0
    with open(file_name, "wb") as file:
        for data in response.iter_content(block_size):
            file.write(data)
            progress += len(data)
            print(f"\rDownloading: {progress / total_size * 100:.2f}%", end="")
    print("\nFile downloaded successfully!")

# Upload the downloaded file to Telegram in chunks
async def upload_file(chat_id, file_path):
    chunk_size = 1024 * 1024 * 50  # 50 MB
    file_size = os.path.getsize(file_path)
    num_chunks = math.ceil(file_size / chunk_size)

    with open(file_path, "rb") as file:
        first_chunk = file.read(chunk_size)
        sent_msg = await app.send_document(chat_id=chat_id, document=first_chunk)
        file_id = sent_msg.document.file_id

        for i in range(num_chunks - 1):
            chunk = file.read(chunk_size)
            await app.edit_message_media(chat_id=chat_id, message_id=sent_msg.id, media=chunk, file_id=file_id)
            print(f"Uploaded chunk {i + 2}/{num_chunks}")

    print("File uploaded to Telegram!")
    os.remove(file_path)

# Command handler for /download
@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) > 1:
        url = message.text.split()[1]
        file_name = os.path.basename(url)
        await message.reply_text(f"Downloading file from {url}...")
        await download_file(url, file_name)
        await message.reply_text("Uploading file to Telegram...")
        await upload_file(chat_id, file_name)
    else:
        await message.reply_text("Please provide a URL to download the file from.")

# Start the bot
app.run()
