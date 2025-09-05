import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import white, HexColor, grey
from reportlab.lib.units import inch
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
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/Windows/Fonts/arial.ttf",
            ]

            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
                    return

            print("Warning: No Georgian-compatible font found, using default font")

        except Exception as e:
            print(f"Warning: Could not register custom font: {e}")

    def _setup_styles(self):
        self.styles = getSampleStyleSheet()

        # Define modern colors
        self.primary_color = HexColor("#2563eb")  # Blue
        self.secondary_color = HexColor("#059669")  # Green
        self.accent_color = HexColor("#7c3aed")  # Purple
        self.text_color = HexColor("#1f2937")  # Dark gray
        self.light_grey = HexColor("#f3f4f6")  # Light grey

        # Title style - large and prominent
        self.title_style = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Heading1"],
            fontSize=24,
            spaceAfter=20,
            spaceBefore=10,
            textColor=self.primary_color,
            fontName="DejaVuSans",
            alignment=1,  # Center alignment
        )

        # Subtitle style
        self.subtitle_style = ParagraphStyle(
            "CustomSubtitle",
            parent=self.styles["Heading2"],
            fontSize=16,
            spaceAfter=15,
            spaceBefore=10,
            textColor=self.secondary_color,
            fontName="DejaVuSans",
        )

        # Section heading style
        self.heading_style = ParagraphStyle(
            "CustomHeading",
            parent=self.styles["Heading2"],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=self.accent_color,
            fontName="DejaVuSans",
            borderWidth=0,
            borderPadding=5,
            leftIndent=0,
        )

        # Improved normal text style
        self.normal_style = ParagraphStyle(
            "CustomNormal",
            parent=self.styles["Normal"],
            fontSize=11,
            fontName="DejaVuSans",
            spaceAfter=6,
            textColor=self.text_color,
            leading=14,
        )

        # Bold text style
        self.bold_style = ParagraphStyle(
            "CustomBold",
            parent=self.normal_style,
            fontSize=11,
            fontName="DejaVuSans",
            textColor=self.text_color,
            spaceAfter=8,
        )

        # Header style
        self.header_style = ParagraphStyle(
            "HeaderStyle",
            parent=self.styles["Normal"],
            fontSize=10,
            fontName="DejaVuSans",
            textColor=grey,
            alignment=2,  # Right alignment
        )

    def generate_summary_pdf(self, summarized_data, output_path):
        try:
            # Setup document with margins
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=50,
                leftMargin=50,
                topMargin=50,
                bottomMargin=50,
            )
            story = []

            # Header with date
            current_date = datetime.now().strftime("%B %d, %Y")
            story.append(Paragraph(f"Generated on {current_date}", self.header_style))
            story.append(Spacer(1, 20))

            # Main Title with professional styling
            story.append(Paragraph("📊 Financial Analysis Report", self.title_style))
            story.append(Spacer(1, 10))
            story.append(
                Paragraph("Comprehensive Financial Data Summary", self.subtitle_style)
            )
            story.append(Spacer(1, 30))

            # Executive Summary Section
            if summarized_data:
                story.append(Paragraph("📋 Executive Summary", self.heading_style))
                story.append(Spacer(1, 15))

                # Create a beautiful table for key metrics if data is structured
                if isinstance(summarized_data, dict):
                    # Extract key financial metrics for highlight table
                    key_metrics = self._extract_key_metrics(summarized_data)
                    if key_metrics:
                        story.append(
                            Paragraph("Key Financial Highlights", self.bold_style)
                        )
                        story.append(Spacer(1, 10))

                        # Create metrics table
                        table_data = [["Metric", "Value"]]
                        for metric, value in key_metrics.items():
                            table_data.append([metric, value])

                        table = Table(table_data, colWidths=[3 * inch, 2 * inch])
                        table.setStyle(
                            TableStyle(
                                [
                                    ("BACKGROUND", (0, 0), (-1, 0), self.primary_color),
                                    ("TEXTCOLOR", (0, 0), (-1, 0), white),
                                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                                    ("FONTNAME", (0, 0), (-1, 0), "DejaVuSans"),
                                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                                    ("BACKGROUND", (0, 1), (-1, -1), self.light_grey),
                                    ("FONTNAME", (0, 1), (-1, -1), "DejaVuSans"),
                                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                                    ("GRID", (0, 0), (-1, -1), 1, self.text_color),
                                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                                ]
                            )
                        )
                        story.append(table)
                        story.append(Spacer(1, 20))

                    # Detailed sections using existing recursive method
                    story.append(Paragraph("📈 Detailed Analysis", self.heading_style))
                    story.append(Spacer(1, 15))
                    self._process_data_recursively(summarized_data, story)

                else:
                    # For non-dict data, use the existing recursive method
                    self._process_data_recursively(summarized_data, story)

            # Footer section
            story.append(Spacer(1, 30))
            story.append(
                Paragraph(
                    "Generated by NGL Financial Analysis System", self.header_style
                )
            )

            doc.build(story)
            return {"success": True, "file_path": output_path}

        except Exception as e:
            return {"success": False, "error": f"PDF generation failed: {str(e)}"}

    def _sanitize_text(self, text):
        if not isinstance(text, str):
            text = str(text)

        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")

        return text

    def _format_key(self, key):
        return key.replace("_", " ").replace("-", " ").title()

    def _process_data_recursively(self, data, story, level=0, max_level=5):
        if level > max_level:
            story.append(Paragraph("... (data too deeply nested)", self.normal_style))
            return

        if isinstance(data, dict):
            for key, value in data.items():
                formatted_key = self._format_key(key)
                sanitized_key = self._sanitize_text(formatted_key)

                if isinstance(value, dict):
                    story.append(
                        Paragraph(
                            f"<b>{sanitized_key}</b>",
                            self.heading_style if level == 0 else self.normal_style,
                        )
                    )
                    self._process_data_recursively(value, story, level + 1, max_level)
                    story.append(Spacer(1, 8 if level == 0 else 4))
                elif isinstance(value, list):
                    story.append(
                        Paragraph(
                            f"<b>{sanitized_key}</b>",
                            self.heading_style if level == 0 else self.normal_style,
                        )
                    )
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            story.append(Paragraph(f"Item {i+1}:", self.normal_style))
                            self._process_data_recursively(
                                item, story, level + 1, max_level
                            )
                        else:
                            sanitized_item = self._sanitize_text(item)
                            story.append(
                                Paragraph(f"• {sanitized_item}", self.normal_style)
                            )
                    story.append(Spacer(1, 8 if level == 0 else 4))
                else:
                    sanitized_value = self._sanitize_text(value)
                    if level == 0:
                        story.append(
                            Paragraph(
                                f"<b>{sanitized_key}</b>: {sanitized_value}",
                                self.normal_style,
                            )
                        )
                    else:
                        story.append(
                            Paragraph(
                                f"• {sanitized_key}: {sanitized_value}",
                                self.normal_style,
                            )
                        )
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

    def _extract_key_metrics(self, data):
        """Extract key financial metrics for the highlight table"""
        metrics = {}

        # Look for common financial metrics
        if "company_name" in data:
            metrics["Company"] = data["company_name"]

        if "currency" in data:
            metrics["Currency"] = data["currency"]

        if "reporting_period" in data:
            metrics["Period"] = data["reporting_period"]

        # Look for revenue/income data
        for key, value in data.items():
            if "revenue" in key.lower() or "income" in key.lower():
                if isinstance(value, (int, float)) and value != 0:
                    metrics[key.replace("_", " ").title()] = self._format_currency(
                        value
                    )
                    break

        # Look for profit data
        for key, value in data.items():
            if "profit" in key.lower() or "earnings" in key.lower():
                if isinstance(value, (int, float)) and value != 0:
                    metrics[key.replace("_", " ").title()] = self._format_currency(
                        value
                    )
                    break

        return metrics if len(metrics) > 1 else {}

    def _format_value(self, value):
        """Format values for display"""
        if isinstance(value, (int, float)):
            if abs(value) > 1000:
                return self._format_currency(value)
            return str(value)
        return str(value)

    def _format_currency(self, amount):
        """Format currency amounts"""
        if abs(amount) >= 1000000:
            return f"{amount/1000000:.1f}M"
        elif abs(amount) >= 1000:
            return f"{amount/1000:.1f}K"
        else:
            return f"{amount:,.0f}"
