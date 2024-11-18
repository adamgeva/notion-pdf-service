import logging
import logging.handlers
import os
from pathlib import Path

# Create logs directory if it doesn't exist
logs_dir = Path(__file__).parent.parent / 'logs'
logs_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console handler
        logging.handlers.RotatingFileHandler(
            logs_dir / 'app.log',
            maxBytes=1024 * 1024,  # 1MB
            backupCount=5
        )
    ]
)