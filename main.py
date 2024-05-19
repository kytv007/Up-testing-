import os
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


import requests
import math
from urllib.parse import urlparse
from pyrogram import Client, filters


API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("hash")
BOT_TOKEN = os.environ.get("Token")

# Create a Pyrogram client instance
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, session_string=None)



# Create the "downloads" folder if it doesn't exist
downloads_dir = "downloads"
if not os.path.exists(downloads_dir):
    os.makedirs(downloads_dir)

# Download a file from a URL in chunks
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
# Upload a file to Telegram in chunks
import time


class TimeFormatter:
    def __init__(self, milliseconds):
        self.milliseconds = milliseconds

    def format(self):
        seconds, milliseconds = divmod(self.milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return "{:02}:{:02}:{:02}".format(hours, minutes, seconds)

async def upload_file(chat_id, file_path):
    try:
        chunk_size = 1024 * 1024 * 45
        file_size = os.path.getsize(file_path)
        num_chunks = math.ceil(file_size / chunk_size)
        start_time = time.time()
        with open(file_path, "rb") as file:  # Open the file in binary mode
            sent_msg = await app.send_document(chat_id=chat_id, document=file_path)
            if sent_msg and sent_msg.document:
                file_id = sent_msg.document.file_id
                for i in range(num_chunks - 1):
                    chunk = file.read(chunk_size)
                    await app.send_chat_action(chat_id, "upload_document")
                    await app.edit_message_media(chat_id=chat_id, message_id=sent_msg.message_id, media=chunk, file_id=file_id)
                    # Calculate progress
                    current_size = (i + 1) * chunk_size
                    progress_message = "[{0}{1}] {2:.2f}%\n".format(
                        ''.join(["█" for i in range(math.floor(current_size / file_size * 20))]),
                        ''.join(["" for i in range(20 - math.floor(current_size / file_size * 20))]),
                        current_size / file_size * 100
                    )
                    # Calculate speed and remaining time
                    now = time.time()
                    elapsed_time = now - start_time
                    speed = current_size / elapsed_time if elapsed_time > 0 else 0
                    remaining_time = (file_size - current_size) / speed if speed > 0 else 0
                    remaining_time_str = TimeFormatter(remaining_time * 1000).format()

                    progress_message += f"Progress: {current_size}/{file_size} bytes\n"
                    progress_message += f"Speed: {speed:.2f} bytes/s\n"
                    progress_message += f"Remaining time: {remaining_time_str}"

                    await app.send_message(chat_id, progress_message)
                    print(f"Uploaded chunk {i + 1}/{num_chunks}")
            else:
                print("Failed to retrieve document information.")
        print("File uploaded to Telegram!")
        os.remove(file_path)
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
