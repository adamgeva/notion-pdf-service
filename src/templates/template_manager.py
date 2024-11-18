from typing import Dict, Any, Optional
from pathlib import Path
import fitz
from dataclasses import dataclass
import yaml
import logging

logger = logging.getLogger(__name__)

@dataclass
class TemplateConfig:
    """Configuration for a PDF template"""
    file_name: str
    field_mappings: Dict[str, str]
    required_notion_fields: set[str]
    conditions: Dict[str, Any]

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'TemplateConfig':
        """Create a TemplateConfig instance from a dictionary"""
        return cls(
            file_name=config_dict['file_name'],
            field_mappings=config_dict['field_mappings'],
            required_notion_fields=set(config_dict['required_notion_fields']),
            conditions=config_dict['conditions']
        )

class Template:
    """Handles template-specific operations"""
    
    def __init__(self, template_path: Path, config: TemplateConfig):
        self.template_path = template_path
        self.config = config

    def validate_data(self, data: Dict[str, Any]) -> None:
        """Validate that all required fields are present in the data"""
        missing_fields = self.config.required_notion_fields - set(data.keys())
        if missing_fields:
            logger.error(f"Missing required fields in data: {missing_fields}")
            raise ValueError(f"Missing required fields: {missing_fields}")

    def validate_template_fields(self) -> None:
        """Validate that all required PDF fields exist in the template"""
        try:
            with fitz.open(self.template_path) as doc:
                template_fields = {w.field_name for page in doc for w in page.widgets()}
                required_fields = set(self.config.field_mappings.values())
                missing_fields = required_fields - template_fields
                if missing_fields:
                    logger.error(f"Template missing required fields: {missing_fields}")
                    raise ValueError(f"Template missing required fields: {missing_fields}")
        except Exception as e:
            logger.error(f"Failed to validate template fields: {str(e)}")
            raise

    def map_data_to_template(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Map Notion data to PDF template fields"""
        return {
            pdf_field: str(data.get(notion_field, ''))
            for notion_field, pdf_field in self.config.field_mappings.items()
        }

    def process_data(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Process data through validation and mapping"""
        self.validate_data(data)
        self.validate_template_fields()
        processed_data = self.map_data_to_template(data)
        logger.debug(f"Data processed successfully for template: {self.template_path.name}")
        return processed_data

class TemplateCatalog:
    """Catalog of available PDF templates and their configurations"""
    
    def __init__(self, templates_dir: Path, config_path: Path):
        self.templates_dir = templates_dir
        self.templates = self._load_template_configs(config_path)
        logger.info(f"Template catalog initialized with {len(self.templates)} templates")

    def _load_template_configs(self, config_path: Path) -> Dict[str, TemplateConfig]:
        """Load template configurations from YAML file"""
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            return {
                template_type: TemplateConfig.from_dict(template_config)
                for template_type, template_config in config_data['templates'].items()
            }
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            raise ValueError(f"Error parsing YAML config: {e}")
        except KeyError as e:
            logger.error(f"Invalid config structure: {e}")
            raise ValueError(f"Invalid config structure: {e}")

    def determine_template(self, data: Dict[str, Any]) -> str:
        """
        Determine which template to use based on the data
        Returns template_type or raises ValueError if no match
        """
        for template_type, config in self.templates.items():
            if all(
                data.get(key) == value 
                for key, value in config.conditions.items()
            ):
                logger.info(f"Template type determined: {template_type}")
                return template_type
                
        logger.error("No matching template found for the provided data")
        raise ValueError("No matching template found for the provided data")

    def get_template(self, template_type: str) -> Template:
        """Get template instance by type"""
        if template_type not in self.templates:
            logger.error(f"Unknown template type: {template_type}")
            raise ValueError(f"Unknown template type: {template_type}")
            
        config = self.templates[template_type]
        template_path = self.templates_dir / config.file_name
        return Template(template_path, config)

def main():
    """Example usage of the template system"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Setup paths
    base_dir = Path(__file__).parent.parent.parent
    templates_dir = base_dir / "templates"
    config_path = templates_dir / "templates_config.yaml"

    logger.info(f'Initializing with templates directory: {templates_dir}')
    logger.info(f'Using config file: {config_path}')

    try:
        # Initialize the catalog
        catalog = TemplateCatalog(templates_dir, config_path)

        # Example Notion data
        notion_data = {
            "provider": "migdal",
            "id": "12345",
            "name_hebrew": "שם",
            "name_english": "Name"
        }

        # Determine which template to use
        template_type = catalog.determine_template(notion_data)
        logger.info(f"Selected template: {template_type}")

        # Get the template
        template = catalog.get_template(template_type)

        # Process the data (includes validation and mapping)
        processed_data = template.process_data(notion_data)
        logger.info("Data processed successfully")
        logger.debug("Processed data:")
        for pdf_field, value in processed_data.items():
            logger.debug(f"{pdf_field}: {value}")

    except Exception as e:
        logger.error(f"Template processing failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()