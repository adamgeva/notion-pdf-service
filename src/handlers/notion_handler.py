"""
Notion API handler for managing page operations and data parsing.
"""

from notion_client import Client
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import logging
from src.config import config

logger = logging.getLogger(__name__)

class NotionPropertiesBuilder:
    @staticmethod
    def title(content: str) -> Dict[str, Any]:
        """
        Create a title property.
        Example: page_title = "My Page"
        """
        return {
            "title": [
                {
                    "text": {
                        "content": content
                    }
                }
            ]
        }

    @staticmethod
    def rich_text(content: str) -> Dict[str, Any]:
        """
        Create a rich text property.
        Example: description = "This is a description"
        """
        return {
            "rich_text": [
                {
                    "text": {
                        "content": content
                    }
                }
            ]
        }

    @staticmethod
    def number(number: Union[int, float]) -> Dict[str, Any]:
        """
        Create a number property.
        Example: count = 42
        """
        return {
            "number": number
        }

    @staticmethod
    def select(option_name: str) -> Dict[str, Any]:
        """
        Create a select property.
        Example: status = "In Progress"
        """
        return {
            "select": {
                "name": option_name
            }
        }

    @staticmethod
    def multi_select(option_names: List[str]) -> Dict[str, Any]:
        """
        Create a multi-select property.
        Example: tags = ["Important", "Urgent"]
        """
        return {
            "multi_select": [
                {"name": name} for name in option_names
            ]
        }

    @staticmethod
    def date(
        start: Union[str, datetime],
        end: Optional[Union[str, datetime]] = None,
        include_time: bool = False
    ) -> Dict[str, Any]:
        """
        Create a date property.
        Example: due_date = datetime.now()
        """
        if isinstance(start, datetime):
            start = start.isoformat() if include_time else start.date().isoformat()
        if isinstance(end, datetime):
            end = end.isoformat() if include_time else end.date().isoformat()

        date_dict = {"start": start}
        if end:
            date_dict["end"] = end

        return {
            "date": date_dict
        }

    @staticmethod
    def checkbox(checked: bool) -> Dict[str, Any]:
        """
        Create a checkbox property.
        Example: is_complete = True
        """
        return {
            "checkbox": checked
        }

    @staticmethod
    def url(url: str) -> Dict[str, Any]:
        """
        Create a URL property.
        Example: website = "https://example.com"
        """
        return {
            "url": url
        }

    @staticmethod
    def email(email: str) -> Dict[str, Any]:
        """
        Create an email property.
        Example: contact = "user@example.com"
        """
        return {
            "email": email
        }

    @staticmethod
    def phone_number(phone: str) -> Dict[str, Any]:
        """
        Create a phone number property.
        Example: phone = "+1234567890"
        """
        return {
            "phone_number": phone
        }

    @staticmethod
    def people(people_ids: List[str]) -> Dict[str, Any]:
        """
        Create a people property.
        Example: assignees = ["user_id_1", "user_id_2"]
        """
        return {
            "people": [
                {"id": person_id} for person_id in people_ids
            ]
        }
    
    @staticmethod
    def external_file(file_name: str, file_url: str) -> Dict[str, Any]:
        """
        Create an external file property.
        Example: document = ("report.pdf", "https://example.com/files/report.pdf")
        """
        return {
            "files": [
                {
                    "name": file_name,
                    "type": "external",
                    "external": {
                        "url": file_url
                    }
                }
            ]
        }

    @staticmethod
    def external_files(files: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Create a property with multiple external files.
        Example: documents = [
            {"name": "report1.pdf", "url": "https://example.com/files/report1.pdf"},
            {"name": "report2.pdf", "url": "https://example.com/files/report2.pdf"}
        ]
        """
        return {
            "files": [
                {
                    "name": file["name"],
                    "type": "external",
                    "external": {
                        "url": file["url"]
                    }
                }
                for file in files
            ]
        }

class NotionUtils:
    @staticmethod
    def extract_page_id(url: str) -> str:
        """
        Extract and format the page ID from a Notion URL following official Notion documentation.
        The function isolates the 32-character ID and formats it with hyphens (8-4-4-4-12 pattern).
        
        Args:
            url (str): The Notion URL
            
        Returns:
            str: The formatted page ID
            
        Raises:
            ValueError: If the URL doesn't contain a valid 32-character Notion page ID
        """
        try:
            # Get the last part of the URL
            last_part = url.strip().split('/')[-1]
            
            # Remove URL parameters if present
            if '?' in last_part:
                last_part = last_part.split('?')[0]
            
            # Extract the 32-character ID
            raw_id = last_part[-32:] if len(last_part) > 32 else last_part
                
            # Validate the ID length
            if len(raw_id) != 32:
                raise ValueError("Invalid Notion page ID: Must be 32 characters long")
            
            # Format the ID with hyphens in the 8-4-4-4-12 pattern
            return f"{raw_id[0:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:32]}"
        except Exception as e:
            logger.error(f"Failed to extract page ID from URL: {url}")
            raise

    @staticmethod
    def parse_property_value(property_data: Dict[str, Any]) -> Any:
        """
        Parse a single Notion property value based on its type.
        
        Args:
            property_data: Dictionary containing property data from Notion API
            
        Returns:
            Parsed property value
        """
        def parse_files(x):
            files = []
            for file_obj in x.get('files', []):
                file_info = {
                    'name': file_obj.get('name', '')
                }
                
                if file_obj.get('type') == 'external':
                    file_info['url'] = file_obj.get('external', {}).get('url', '')
                    file_info['type'] = 'external'
                else:  # type == 'file'
                    file_info['url'] = file_obj.get('file', {}).get('url', '')
                    file_info['expiry_time'] = file_obj.get('file', {}).get('expiry_time', '')
                    file_info['type'] = 'file'
                    
                files.append(file_info)
            return files

        prop_type = property_data.get('type')
        
        type_handlers = {
            'title': lambda x: x.get('title', [{}])[0].get('text', {}).get('content', ''),
            'rich_text': lambda x: x.get('rich_text', [{}])[0].get('text', {}).get('content', '') if x.get('rich_text') else '',
            'select': lambda x: x.get('select', {}).get('name', ''),
            'number': lambda x: x.get('number', 0),
            'date': lambda x: x.get('date', {}).get('start', '') if x.get('date') else '',
            'files': parse_files,
            'file': parse_files  # Some properties might use 'file' instead of 'files'
        }
        
        handler = type_handlers.get(prop_type)
        return handler(property_data) if handler else None

class NotionHandler:
    """
    Main handler for Notion API operations.
    """
    
    def __init__(self, auth_token: str = None):
        """
        Initialize the Notion handler with authentication.
        
        Args:
            auth_token: Optional override for Notion API authentication token
        """
        try:
            self.client = Client(auth=auth_token or config.NOTION_SECRET)
            self.utils = NotionUtils()
            logger.info("Notion client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Notion client")
            raise

    def get_record(self, page_id: str) -> Dict[str, Any]:
        """
        Retrieve a page record from Notion.
        
        Args:
            page_id: The ID of the page to retrieve
            
        Returns:
            Dictionary containing page data
        """
        try:
            logger.info(f"Retrieving Notion page: {page_id}")
            return self.client.pages.retrieve(page_id=page_id)
        except Exception as e:
            logger.error(f"Failed to retrieve Notion page: {page_id}")
            raise
    
    def get_record_from_url(self, url: str) -> Dict[str, Any]:
        """
        Retrieve a page record using its URL.
        
        Args:
            url: The Notion page URL
            
        Returns:
            Dictionary containing page data
        """
        page_id = self.utils.extract_page_id(url)
        return self.get_record(page_id)
    
    def parse_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a Notion page record into a simplified form.
        
        Args:
            record: Raw page record from Notion API
            
        Returns:
            Dictionary containing parsed form data
        """
        try:
            form_data = {}
            properties = record.get('properties', {})
            
            for key, value in properties.items():
                parsed_value = self.utils.parse_property_value(value)
                if parsed_value is not None:
                    form_data[key.lower()] = parsed_value
            
            logger.debug(f"Successfully parsed Notion record")
            return form_data
        except Exception as e:
            logger.error("Failed to parse Notion record")
            raise
    
    def update_page_properties(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update properties of a Notion page.
        
        Args:
            page_id: The ID of the page to update
            properties: Dictionary of properties to update
            
        Returns:
            Updated page record
        """
        try:
            logger.info(f"Updating Notion page: {page_id}")
            result = self.client.pages.update(page_id=page_id, properties=properties)
            logger.info(f"Successfully updated Notion page: {page_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update Notion page: {page_id}")
            raise

def main():
    """Main function for testing the Notion handler."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    notion = NotionHandler()
    test_page_id = "609fa60b-c287-4b47-89e0-2e2923eeea23"
    
    try:
        record = notion.get_record(test_page_id)
        form_data = notion.parse_record(record)

        builder = NotionPropertiesBuilder()
        properties = {
            "Status": builder.rich_text("Success"),
            "pdf": builder.external_file(
                file_name="report.pdf",
                file_url="https://drive.google.com/file/d/1uJ0QPtaohP6HHAnQBsd8vnhrq7ch3Mel/view?usp=drive_link"
            )
        }

        notion.update_page_properties(test_page_id, properties)
        logger.info("Notion test completed successfully")

    except Exception as e:
        logger.error("Notion test failed", exc_info=True)
        raise

if __name__ == "__main__":
    main()