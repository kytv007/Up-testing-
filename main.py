import os
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
import shutil
import requests
import math
from urllib.parse import urlparse
from pyrogram import Client, filters


API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")


app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

downloads_dir = "downloads"
if not os.path.exists(downloads_dir):
    os.makedirs(downloads_dir)


def human_readable_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(min(len(size_name) - 1, max(0, size_bytes.bit_length() - 1) // 10))
    p = pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


async def download_file(url, chat_id, filename, progress_message):
    try:
        temp_file_name = os.path.join(downloads_dir, "temp_file")
        counter = 1
        while os.path.exists(temp_file_name):
            temp_file_name = os.path.join(downloads_dir, f"temp_file_{counter}")
            counter += 1

        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))
        block_size = 1024 * 1024 * 5
        progress = 0
        with open(temp_file_name, "wb") as file:
            for data in response.iter_content(block_size):
                file.write(data)
                progress += len(data)
                percentage = (progress / total_size) * 100
                await progress_message.edit_text(f"Downloading to my server: {percentage:.2f}%")

        await progress_message.edit_text("File downloaded to server successfully!")

        file_name = os.path.join(downloads_dir, filename)
        shutil.move(temp_file_name, file_name)

        return file_name
    except requests.exceptions.RequestException as e:
        await progress_message.edit_text(f"Error downloading file: {e}")
        return None
    except Exception as e:
        await progress_message.edit_text(f"An unexpected error occurred: {e}")
        return None


async def upload_file(chat_id, file_path, filename, progress_message):
    try:
        chunk_size = 1024 * 1024 * 1
        file_size = os.path.getsize(file_path)
        num_chunks = math.ceil(file_size / chunk_size)

        async def progress_callback(current, total):
            percentage = (current / total) * 100
            await progress_message.edit_text(f"Uploading: {percentage:.2f}%")

        sent_msg = await app.send_document(
            chat_id=chat_id,
            document=file_path,
            file_name=filename,
            progress=progress_callback
        )

        if sent_msg and any(getattr(sent_msg, attr, None) for attr in ['document', 'video', 'audio']):
            logger.info("File uploaded to Telegram!")
            await progress_message.edit_text("File uploaded successfully!")
        else:
            logger.error("Failed to retrieve document information.")
            await progress_message.edit_text("Failed to upload the file.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        await progress_message.edit_text(f"An unexpected error occurred: {e}")
        raise
    finally:
        # Remove all files from the downloads directory after upload
        for file in os.listdir(downloads_dir):
            file_path = os.path.join(downloads_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)


@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) > 1:
        url = message.text.split()[1]

        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            response.raise_for_status()

            filename_with_extension = None
            method = None
            if 'Content-Disposition' in response.headers:
                content_disposition = response.headers['Content-Disposition']
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[-1].strip('"')
                    filename_with_extension = filename
                    method = "extracted"

            if filename_with_extension is None:
                parsed_url = urlparse(url)
                filename = parsed_url.path.split("/")[-1]
                filename_with_extension = filename
                method = "fallback"

            logger.info(f"Filename: {filename_with_extension} (Method: {method})")

            if 'Content-Length' in response.headers:
                file_size = int(response.headers['Content-Length'])
                human_readable = human_readable_size(file_size)
                file_info_message = f"Filename: {filename_with_extension}\n\nFile Size: {human_readable}"
            else:
                file_info_message = f"Filename: {filename_with_extension}\n\nFile Size: Not available"

            await app.send_message(chat_id, file_info_message)

            progress_message = await app.send_message(chat_id, "Starting download...")
            file_path = await download_file(url, chat_id, filename_with_extension, progress_message)
            if file_path:
                await upload_file(chat_id, file_path, filename_with_extension, progress_message)
        except requests.exceptions.RequestException as e:
            await app.send_message(chat_id, f"Error retrieving file information: {e}")
        except Exception as e:
            await app.send_message(chat_id, f"An unexpected error occurred: {e}")
    else:
        await message.reply_text("Please provide a URL to download the file from.")


app.run()
