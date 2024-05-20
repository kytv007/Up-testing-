import os
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import requests
import math
from urllib.parse import urlparse
from pyrogram import Client, filters
import tempfile

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")


# Create a Pyrogram client instance
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, session_string=None)


# Create the "downloads" folder if it doesn't exist
downloads_dir = "downloads"
if not os.path.exists(downloads_dir):
    os.makedirs(downloads_dir)

# Download a file from a URL in chunks
async def download_file(url, chat_id):
    try:
        # Get filename and extension from the URL
        url_components = urlparse(url)
        filename = os.path.basename(url_components.path)
        filename_parts = filename.split(".")
        file_extension = filename_parts[-1] if len(filename_parts) > 1 else ""

        # Generate a unique filename
        file_name = os.path.join(downloads_dir, filename)
        counter = 1
        while os.path.exists(file_name):
            file_name = os.path.join(downloads_dir, f"{filename_parts[0]}_{counter}.{file_extension}")
            counter += 1

        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for non-2xx status codes
        total_size = int(response.headers.get("content-length", 0))
        block_size = 1024 * 1024 * 5
        progress = 0
        progress_message = await app.send_message(chat_id, "Downloading: 0%")
        with open(file_name, "wb") as file:
            for data in response.iter_content(block_size):
                file.write(data)
                progress += len(data)
                percentage = (progress / total_size) * 100
                await progress_message.edit_text(f"Downloading: {percentage:.2f}%")

        await progress_message.edit_text("File downloaded successfully!")
        return file_name
    except requests.exceptions.RequestException as e:
        await app.send_message(chat_id, f"Error downloading file: {e}")
    except Exception as e:
        await app.send_message(chat_id, f"An unexpected error occurred: {e}")


# Upload the file

async def upload_file(chat_id, file_path):
    try:
        chunk_size = 1024 * 1024 * 1
        file_size = os.path.getsize(file_path)
        num_chunks = math.ceil(file_size / chunk_size)
        progress_message = await app.send_message(chat_id, "Uploading: 0%")

        combined_chunks = bytearray()
        with open(file_path, "rb") as file:
            for i in range(num_chunks):
                chunk = file.read(chunk_size)
                combined_chunks.extend(chunk)

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as temp_file:
            temp_file.write(combined_chunks)
            temp_file_path = temp_file.name

        async def progress_callback(current, total):
            percentage = (current / total) * 100
            await progress_message.edit_text(f"Uploading: {percentage:.2f}%")

        sent_msg = await app.send_document(chat_id=chat_id, document=temp_file_path, progress=progress_callback)
        if sent_msg and sent_msg.document:
            print("File uploaded to Telegram!")
        else:
            print("Failed to retrieve document information.")

        os.remove(file_path)
        os.remove(temp_file_path)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise

# Command handler for /download
@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) > 1:
        url = message.text.split()[1]
        file_path = await download_file(url, chat_id)
        if file_path:
            await upload_file(chat_id, file_path)
    else:
        await message.reply_text("Please provide a URL to download the file from.")

# Start the bot
app.run()
