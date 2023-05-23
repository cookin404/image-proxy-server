import requests
from flask import send_file
from PIL import Image
import os


def download_image(url, file_path):
    # Send a GET request to the specified URL and save the image to the file path
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36'}, stream=True)
    
    if response.status_code == 200:
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
    else:
        raise Exception('Failed to fetch the image')


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
