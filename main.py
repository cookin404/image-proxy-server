import os
from Server.image_proxy_server import app
from dotenv import load_dotenv

if __name__ == '__main__':
    # Load environment variables from .env file
    load_dotenv()

    # Retrieve the port from the environment variables, defaulting to 3000 if not specified
    port = int(os.getenv('PORT', 3000))

    # Start the Flask app on the specified port
    app.run(port=port)
