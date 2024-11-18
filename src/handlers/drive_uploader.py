from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from typing import Optional, Dict, Any, Union
from pathlib import Path
import logging
from src.config import config

logger = logging.getLogger(__name__)

class DriveUploader:
    def __init__(self, folder_id: Optional[str] = None):
        """
        Initialize the Drive uploader
        
        Args:
            folder_id: Optional Google Drive folder ID to upload to
        """
        self.folder_id = folder_id or config.DRIVE_FOLDER_ID
        self.scopes = ['https://www.googleapis.com/auth/drive.file']
        
        try:
            credentials = service_account.Credentials.from_service_account_file(
                config.SA_PATH, scopes=self.scopes)
            self.service = build('drive', 'v3', credentials=credentials)
            logger.info("Drive service initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Drive service")
            raise

    def upload_file(self, file_path: Union[str, Path], filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a file to Google Drive
        
        Args:
            file_path: Path to the file to upload (can be string or Path object)
            filename: Optional name for the file in Drive
        
        Returns:
            Dict containing file metadata including 'id' and 'webViewLink'
        """
        try:
            file_path_str = str(file_path)
            actual_filename = filename or file_path_str.split('/')[-1]
            logger.info(f"Starting upload of file: {actual_filename}")
            
            file_metadata = {'name': actual_filename}
            if self.folder_id:
                file_metadata['parents'] = [self.folder_id]
                logger.debug(f"Uploading to folder: {self.folder_id}")
            
            media = MediaFileUpload(
                file_path_str,
                mimetype='application/pdf',
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            logger.info(f"File uploaded successfully. ID: {file.get('id')}")
            return file
            
        except Exception as e:
            logger.error(f"Failed to upload file {file_path_str}", exc_info=True)
            raise

    def get_file_link(self, file_id: str) -> str:
        """
        Get the shareable link for a file
        
        Args:
            file_id: The ID of the file in Drive
            
        Returns:
            Shareable link to the file
        """
        try:
            logger.info(f"Setting sharing permissions for file: {file_id}")
            
            # Update file permissions to make it viewable by anyone with the link
            self.service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'},
                fields='id'
            ).execute()
            
            # Get the web view link
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            link = file.get('webViewLink')
            logger.info(f"Shareable link created for file: {file_id}")
            return link
            
        except Exception as e:
            logger.error(f"Failed to create shareable link for file: {file_id}", exc_info=True)
            raise

# Usage example
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize uploader
        uploader = DriveUploader()
        
        # Upload file
        example_path = Path(__file__).parent.parent.parent / "templates" / "migdal.pdf"
        
        file = uploader.upload_file(example_path)
        link = uploader.get_file_link(file['id'])
        
        logger.info(f"Process completed successfully")
        logger.info(f"File ID: {file['id']}")
        logger.info(f"Shareable link: {link}")
        
    except Exception as e:
        logger.error("Process failed", exc_info=True)
        raise