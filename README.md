# Image Proxy Server

The Image Proxy Server is a web application built with Flask that serves as a proxy for fetching and resizing images from remote URLs. It allows you to download images from URLs, store them locally, and resize them based on provided dimensions.

## Features

- Download images from remote URLs
- Store downloaded images locally
- Resize images based on provided dimensions
- Serve resized or original images via HTTP

## Prerequisites

- Python 3.x
- pip package manager

## Installation

1. Clone the repository:
   ```git clone <repository_url>```
2. Navigate to the project directory:
   ```cd image-proxy-server```
3. Create a virtual environment (optional but recommended):
   ```python -m venv venv```
4. Activate the virtual environment (optional):
   ```source venv/bin/activate```
5. Install the required dependencies:
   ```pip install -r requirements.txt```

## Configuration

1. Create a `.env` file in the root directory of the project.
2. Specify the required configuration variables in the `.env` file. For example:

```PORT=3000```

Adjust the port number according to your preference.

## Usage

1. Start the server:
    ```python main.py```
2. The server will be running at `http://localhost:3000` (or the specified port).
3. Make HTTP requests to the server endpoints to proxy and resize images. See the API documentation for details.

## API Documentation

### Proxy and Resize Image

**Endpoint**: `/proxy?url=<image_url>&width=<width>&height=<height>`

- `image_url` (required): The URL of the image to proxy and resize.
- `width` (optional): The desired width of the resized image.
- `height` (optional): The desired height of the resized image.

Example:
GET /proxy?url=https://example.com/image.jpg&width=400&height=300

The server will download the image from the specified URL, resize it to the provided dimensions (if specified), and return the resized or original image.

### Heartbeat

**Endpoint**: `/heartbeat`

A simple endpoint to check if the server is running. It returns an "Alive" response.

GET /heartbeat

## License

This project is licensed under the MIT License.
