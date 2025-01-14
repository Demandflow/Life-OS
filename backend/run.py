import logging
from app import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

if __name__ == '__main__':
    logger.info("Starting server on http://localhost:5003")
    app.run(host='127.0.0.1', port=5003, debug=True)