from flask import Flask, request, send_file
from Utils.image_utils import download_image, get_file_response, resize_image

import hashlib
import os

app = Flask(__name__)
PATH_TO_ASSETS = './src/assets/'
MAX_DIMENSION = 4096

if not os.path.exists(PATH_TO_ASSETS):
    os.makedirs(PATH_TO_ASSETS)


def parse_size(width, height):
    # Return (width, height) as ints, or None unless both are given.
    # The values end up in a cache file name, so they must be validated first.
    if not (width and height):
        return None

    size = (int(width), int(height))
    if not all(1 <= value <= MAX_DIMENSION for value in size):
        raise ValueError('dimension out of range')
    return size


@app.route('/proxy', methods=['GET'])
def handle_proxy_request():
    url = request.args.get('url')

    if not url:
        return 'URL is required', 400

    try:
        size = parse_size(request.args.get('width'), request.args.get('height'))
    except ValueError:
        return f'width and height must be integers from 1 to {MAX_DIMENSION}', 400

    hash_value = hashlib.md5(url.encode()).hexdigest()

    original_path = f'{PATH_TO_ASSETS}{hash_value}.jpg'
    target_path = original_path
    if size:
        target_path = f'{PATH_TO_ASSETS}{hash_value}_{size[0]}x{size[1]}.jpg'

    file_response = get_file_response(target_path)
    if file_response:
        return file_response

    try:
        if not os.path.exists(original_path):
            download_image(url, original_path)

        if size:
            resize_image(original_path, target_path, *size)

        return send_file(target_path, mimetype='image/jpeg')
    except Exception as e:
        print(e)
        return 'Error: Failed to fetch or resize the image', 500


@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    return 'Alive'
