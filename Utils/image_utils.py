from flask import send_file
from PIL import Image
from urllib.parse import urlsplit
from Utils.safe_http import BlockedURLError, create_session
import os
import tempfile
import time

ALLOWED_SCHEMES = ('http', 'https')
REQUEST_TIMEOUT = (5, 15)  # connect, read between bytes
DOWNLOAD_DEADLINE_SECONDS = 60
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36'


def download_image(url, file_path):
    # Save the image at url to file_path. The file only appears once it is
    # complete and verified, so a failed download never ends up in the cache.
    if urlsplit(url).scheme not in ALLOWED_SCHEMES:
        raise BlockedURLError(f'Scheme not allowed: {url}')

    descriptor, temp_path = tempfile.mkstemp(dir=os.path.dirname(file_path))
    try:
        with os.fdopen(descriptor, 'wb') as file:
            stream_to_file(url, file)

        with Image.open(temp_path) as image:
            image.verify()

        os.replace(temp_path, file_path)
    except Exception:
        os.remove(temp_path)
        raise


def stream_to_file(url, file):
    deadline = time.monotonic() + DOWNLOAD_DEADLINE_SECONDS
    received = 0

    with create_session() as session:
        response = session.get(
            url, headers={'User-Agent': USER_AGENT}, stream=True, timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            raise Exception('Failed to fetch the image')

        for chunk in response.iter_content(chunk_size=1024):
            received += len(chunk)
            if received > MAX_DOWNLOAD_BYTES:
                raise Exception('Image is too large')
            if time.monotonic() >= deadline:
                raise Exception('Download took too long')
            file.write(chunk)


def get_file_response(file_path):
    # Return the file as a Flask send_file response if it exists
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/jpeg')
    return None


def resize_image(original_path, resized_path, width, height):
    # Open the original image, resize it, and save the resized image to the specified path
    with Image.open(original_path) as image:
        resized_image = image.resize((width, height))
        resized_image.save(resized_path, "JPEG")
