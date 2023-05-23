from flask import Flask, request, send_file
from Utils.image_utils import download_image, get_file_response, resize_image

import hashlib
import os

app = Flask(__name__)
PATH_TO_ASSETS = './src/assets/'

if not os.path.exists(PATH_TO_ASSETS):
    os.makedirs(PATH_TO_ASSETS)


@app.route('/proxy', methods=['GET'])
def handle_proxy_request():
    url = request.args.get('url')

    if not url:
        return 'URL is required', 400

    hash_value = hashlib.md5(url.encode()).hexdigest()

    file_path = f'{PATH_TO_ASSETS}{hash_value}.jpg'

    file_response = get_file_response(file_path)
    if file_response:
        return file_response

    try:
        download_image(url, file_path)

        # Check if resize parameters are provided
        width = request.args.get('width')
        height = request.args.get('height')

        # Resize the image if width and height parameters are present
        if width and height:
            resized_file_path = f'{PATH_TO_ASSETS}{hash_value}_resized.jpg'
            resize_image(file_path, resized_file_path, int(width), int(height))
            return send_file(resized_file_path, mimetype='image/jpeg')

        return send_file(file_path, mimetype='image/jpeg')
    except Exception as e:
        print(e)
        return 'Error: Failed to fetch or resize the image', 500


@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    return 'Alive'
