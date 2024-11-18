from pathlib import Path
from typing import Dict, Any
from src.templates.template_manager import TemplateCatalog
from src.handlers.pdf_handler import PDFHandler
import logging
from src.config import config

logger = logging.getLogger(__name__)

class EnhancedPDFHandler:
    def __init__(self, templates_dir: Path = None, config_path: Path = None):
        self.catalog = TemplateCatalog(
            templates_dir or config.TEMPLATES_DIR,
            config_path or config.TEMPLATE_CONFIG_PATH
        )
    def process_and_fill_pdf(self, data: Dict[str, Any], output_path: str) -> str:
        """Process data and fill the appropriate PDF template"""
        try:
            template_type = self.catalog.determine_template(data)
            logger.info(f"Selected template type: {template_type}")
            
            template = self.catalog.get_template(template_type)
            processed_data = template.process_data(data)
            
            pdf_handler = PDFHandler(str(template.template_path))
            result = pdf_handler.fill_pdf(processed_data, output_path)
            
            logger.info(f"PDF generated successfully at: {output_path}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process and fill PDF: {str(e)}")
            raise

# Usage example:
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        base_dir = Path(__file__).parent.parent.parent
        templates_dir = base_dir / "templates"
        config_path = templates_dir / "templates_config.yaml"
        output_path = base_dir / "output.pdf"
        
        pdf_handler = EnhancedPDFHandler(
            templates_dir=templates_dir,
            config_path=config_path
        )
        
        data = {
            "provider": "migdal",
            "id": "12345",
            "name_hebrew": "שם",
            "name_english": "Name"
        }
        
        output_path = pdf_handler.process_and_fill_pdf(
            data=data,
            output_path=output_path
        )
        
    except Exception as e:
        logger.error("PDF processing failed", exc_info=True)