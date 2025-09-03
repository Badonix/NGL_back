import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import black, blue
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime

class PDFGenerator:
    def __init__(self):
        self._register_fonts()
        self._setup_styles()
    
    def _register_fonts(self):
        try:
            font_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/TTF/DejaVuSans.ttf',
                '/System/Library/Fonts/Helvetica.ttc',
                '/Windows/Fonts/arial.ttf'
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                    return
            
            print("Warning: No Georgian-compatible font found, using default font")
            
        except Exception as e:
            print(f"Warning: Could not register custom font: {e}")
    
    def _setup_styles(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            textColor=blue,
            fontName='DejaVuSans'
        )
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            textColor=black,
            fontName='DejaVuSans'
        )
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            fontName='DejaVuSans'
        )
    
    def generate_summary_pdf(self, summarized_data, output_path):
        try:
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            story = []
            
            story.append(Paragraph("Financial Analysis Summary", self.title_style))
            story.append(Spacer(1, 12))
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            story.append(Paragraph(f"Generated on: {timestamp}", self.normal_style))
            story.append(Spacer(1, 20))
            
            self._process_data_recursively(summarized_data, story)
            
            doc.build(story)
            return {"success": True, "file_path": output_path}
            
        except Exception as e:
            return {"success": False, "error": f"PDF generation failed: {str(e)}"}
    
    def _sanitize_text(self, text):
        if not isinstance(text, str):
            text = str(text)
        
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        return text
    
    def _format_key(self, key):
        return key.replace('_', ' ').replace('-', ' ').title()
    
    def _process_data_recursively(self, data, story, level=0, max_level=5):
        if level > max_level:
            story.append(Paragraph("... (data too deeply nested)", self.normal_style))
            return
        
        if isinstance(data, dict):
            for key, value in data.items():
                formatted_key = self._format_key(key)
                sanitized_key = self._sanitize_text(formatted_key)
                
                if isinstance(value, dict):
                    story.append(Paragraph(f"<b>{sanitized_key}</b>", self.heading_style if level == 0 else self.normal_style))
                    self._process_data_recursively(value, story, level + 1, max_level)
                    story.append(Spacer(1, 8 if level == 0 else 4))
                elif isinstance(value, list):
                    story.append(Paragraph(f"<b>{sanitized_key}</b>", self.heading_style if level == 0 else self.normal_style))
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            story.append(Paragraph(f"Item {i+1}:", self.normal_style))
                            self._process_data_recursively(item, story, level + 1, max_level)
                        else:
                            sanitized_item = self._sanitize_text(item)
                            story.append(Paragraph(f"• {sanitized_item}", self.normal_style))
                    story.append(Spacer(1, 8 if level == 0 else 4))
                else:
                    sanitized_value = self._sanitize_text(value)
                    if level == 0:
                        story.append(Paragraph(f"<b>{sanitized_key}</b>: {sanitized_value}", self.normal_style))
                    else:
                        story.append(Paragraph(f"• {sanitized_key}: {sanitized_value}", self.normal_style))
                    story.append(Spacer(1, 4))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    story.append(Paragraph(f"Item {i+1}:", self.normal_style))
                    self._process_data_recursively(item, story, level + 1, max_level)
                else:
                    sanitized_item = self._sanitize_text(item)
                    story.append(Paragraph(f"• {sanitized_item}", self.normal_style))
        else:
            sanitized_data = self._sanitize_text(data)
            story.append(Paragraph(sanitized_data, self.normal_style))
