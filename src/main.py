from flask import Flask, request, jsonify
from src.templates.enhanced_pdf_handler import EnhancedPDFHandler
from src.handlers.notion_handler import NotionHandler, NotionPropertiesBuilder
from src.handlers.pdf_handler import PDFHandler
from src.handlers.drive_uploader import DriveUploader
import tempfile
import os
from pathlib import Path
import logging
from contextlib import contextmanager
from typing import Dict, Any, Generator
from src.config import config

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize handlers at startup time
try:
    notion = NotionHandler()
    pdf_handler = EnhancedPDFHandler(
        templates_dir=config.TEMPLATES_DIR,
        config_path=config.TEMPLATE_CONFIG_PATH
    )
    
    # Validate paths exist
    if not config.TEMPLATES_DIR.exists():
        raise FileNotFoundError(f"Templates directory not found: {config.TEMPLATES_DIR}")
    if not config.TEMPLATE_CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {config.TEMPLATE_CONFIG_PATH}")
        
except Exception as e:
    logger.critical(f"Failed to initialize application: {e}")
    raise

@contextmanager
def temp_pdf_file() -> Generator[str, None, None]:
    """Context manager for temporary PDF file handling"""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
            yield tmp_path
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.error(f"Failed to delete temporary file {tmp_path}: {e}")

def parse_request_data() -> Dict[str, Any]:
    """Parse and validate incoming request data"""
    if request.content_type == 'application/json':
        data = request.get_json()
    elif request.content_type == 'application/x-www-form-urlencoded':
        data = request.form.to_dict()
    else:
        raise ValueError(f"Unsupported Content-Type: {request.content_type}")

    if not data or 'url' not in data:
        raise ValueError("Missing required field: url")

    return data

def process_notion_record(url: str) -> tuple[str, Dict[str, Any]]:
    """Process Notion record and return page_id and parsed record"""
    page_id = notion.utils.extract_page_id(url)
    logger.info(f"Processing Notion page: {page_id}")
    
    record = notion.get_record(page_id)
    parsed_record = notion.parse_record(record)
    logger.debug(f"Parsed record: {parsed_record}")
    
    return page_id, parsed_record

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle incoming webhook requests"""
    try:
        # Parse request data
        data = parse_request_data()
        logger.info("Received webhook request")

        # Process Notion record
        page_id, parsed_record = process_notion_record(data["url"])

        # Generate and upload PDF
        with temp_pdf_file() as output_path:
            # Generate PDF
            logger.info("Generating PDF...")
            pdf_handler.process_and_fill_pdf(
                data=parsed_record,
                output_path=output_path
            )

            # Upload to Drive
            logger.info("Uploading to Google Drive...")
            uploader = DriveUploader()  # Config handled in DriveUploader class
            file = uploader.upload_file(output_path)
            link = uploader.get_file_link(file['id'])

            # Update Notion
            logger.info("Updating Notion record...")
            builder = NotionPropertiesBuilder()
            properties = {
                "Status": builder.rich_text("Success"),
                "pdf": builder.external_file(
                    file_name="report.pdf",
                    file_url=link
                )
            }
            notion.update_page_properties(page_id, properties)

        return jsonify({'status': 'success', 'file_link': link}), 200
    
    except ValueError as e:
        # Client errors (bad request data)
        logger.warning(f"Invalid request: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        # Server errors
        logger.error(f"Error processing request", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=config.DEBUG)