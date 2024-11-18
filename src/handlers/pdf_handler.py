import fitz
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

class PDFHandler:
    def __init__(self, template_path: str):
        self.template_path = Path(template_path)
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
            
        try:
            with fitz.open(self.template_path) as doc:
                self.fields = self._get_form_fields(doc)
            logger.info(f"PDF template loaded with fields: {self.fields}")

        except Exception as e:
            logger.error(f"Failed to load PDF template: {str(e)}")
            raise

    def _get_form_fields(self, doc: fitz.Document) -> Dict[str, Dict]:
        fields = {}
        for page in doc:
            widgets = list(page.widgets())
            for widget in widgets:
                field_name = widget.field_name
                fields[field_name] = {
                    'page': page.number,
                    'rect': widget.rect,
                    'font_size': widget.text_font_size if hasattr(widget, 'text_font_size') else 11
                }
        return fields

    def _is_rtl_text(self, text: str) -> bool:
        """
        Check if text contains RTL characters (Hebrew or Arabic)
        """
        rtl_ranges = [
            (0x0590, 0x05FF),  # Hebrew
            (0x0600, 0x06FF),  # Arabic
            (0xFB1D, 0xFB4F),  # Hebrew presentation forms
        ]
        
        for char in text:
            code = ord(char)
            for start, end in rtl_ranges:
                if start <= code <= end:
                    return True
        return False

    def _reverse_rtl_text(self, text: str) -> str:
        """
        Reverse RTL text for proper display
        """
        return text[::-1] if self._is_rtl_text(text) else text

    def _draw_text_as_shape(self, page: fitz.Page, text: str, rect: fitz.Rect, font_size: float = 11):
        """
        Draw text as shapes instead of using form fields
        """
        # Create a text writer
        text_writer = fitz.TextWriter(page.rect)
        
        # Use Times-Roman font for better appearance
        font = fitz.Font("Helvetica")
        
        # Handle RTL text
        is_rtl = self._is_rtl_text(text)
        if is_rtl:
            text = self._reverse_rtl_text(text)
        
        # Calculate text width for positioning
        text_width = font.text_length(text, fontsize=font_size)
        
        # Calculate x position
        if is_rtl:
            # For RTL text, align to right edge minus text width
            x = rect.x1 - text_width
        else:
            # For LTR text, align to left edge
            x = rect.x0
            
        # Vertical center
        y = (rect.y0 + rect.y1) / 2
        
        # Add text
        text_writer.append(
            (x, y),
            text,
            font=font,
            fontsize=font_size
        )
        
        # Convert text to shapes and draw
        text_writer.write_text(page)

    def fill_pdf(self, data: Dict[str, str], output_path: str) -> str:
        """
        Fill PDF by drawing text as shapes
        """
        doc = None
        
        try:
            logger.info(f"Starting to fill PDF with {len(data)} fields")
            doc = fitz.open(self.template_path)
            
            for field_name, value in data.items():
                if field_name not in self.fields:
                    logger.warning(f"Field {field_name} not found in template")
                    continue

                field_info = self.fields[field_name]
                page = doc[field_info['page']]
                
                # Remove form fields by removing their annotations
                for annot in page.annots():
                    if getattr(annot, 'field_name', None) == field_name:
                        page.delete_annot(annot)
                
                # Draw the text as shapes
                self._draw_text_as_shape(
                    page,
                    str(value),
                    field_info['rect'],
                    field_info.get('font_size', 11)
                )

            # Save the document
            doc.save(
                output_path,
                garbage=4,
                deflate=True,
                clean=True,
                pretty=True
            )

            logger.info(f"Successfully filled PDF: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to fill PDF: {str(e)}")
            raise
            
        finally:
            if doc:
                try:
                    doc.close()
                except:
                    pass

# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize handler
    pdf_handler = PDFHandler("/Users/tzvgt8/notion-pdf-service/templates/migdal.pdf")
    
    # Simple data dictionary - just field names and values
    data = {
        'text_1efdg': '300488830',
        'text_2xgca': 'גבע',
        'text_3zmip': 'geva'
    }
    
    # Fill and save PDF
    pdf_handler.fill_pdf(data, "/Users/tzvgt8/notion-pdf-service/output6.pdf")