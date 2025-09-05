import os
import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_agg import FigureCanvasAgg
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.colors import white, black, HexColor, grey, red, green, blue
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
from datetime import datetime
import numpy as np


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

        # Define professional financial colors
        self.primary_color = HexColor("#1f2937")  # Dark Gray (Professional)
        self.secondary_color = HexColor("#059669")  # Green (Positive)
        self.accent_color = HexColor("#dc2626")  # Red (Negative/Alert)
        self.text_color = HexColor("#374151")  # Gray
        self.light_grey = HexColor("#f9fafb")  # Very Light Grey
        self.medium_grey = HexColor("#e5e7eb")  # Medium Grey
        self.blue_accent = HexColor("#3b82f6")  # Blue (Charts)
        self.gold_accent = HexColor("#f59e0b")  # Gold (Highlights)

        # Professional title style
        self.title_style = ParagraphStyle(
            "FinancialTitle",
            parent=self.styles["Heading1"],
            fontSize=28,
            spaceAfter=25,
            spaceBefore=15,
            textColor=self.primary_color,
            fontName="DejaVuSans",
            alignment=1,
            borderWidth=0,
            borderPadding=0,
        )
        
        # Company name style
        self.company_style = ParagraphStyle(
            "CompanyName",
            parent=self.styles["Heading1"],
            fontSize=22,
            spaceAfter=10,
            spaceBefore=5,
            textColor=self.blue_accent,
            fontName="DejaVuSans",
            alignment=1,
        )

        # Financial subtitle style
        self.subtitle_style = ParagraphStyle(
            "FinancialSubtitle",
            parent=self.styles["Heading2"],
            fontSize=18,
            spaceAfter=20,
            spaceBefore=15,
            textColor=self.text_color,
            fontName="DejaVuSans",
            alignment=1,
        )
        
        # Section header style
        self.section_header_style = ParagraphStyle(
            "SectionHeader",
            parent=self.styles["Heading2"],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=white,
            fontName="DejaVuSans",
            backColor=self.primary_color,
            borderPadding=8,
            alignment=0,
        )

        # Financial heading style
        self.heading_style = ParagraphStyle(
            "FinancialHeading",
            parent=self.styles["Heading3"],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=12,
            textColor=self.primary_color,
            fontName="DejaVuSans",
            borderWidth=1,
            borderColor=self.medium_grey,
            borderPadding=5,
            backColor=self.light_grey,
        )
        
        # Key metrics style
        self.metrics_style = ParagraphStyle(
            "KeyMetrics",
            parent=self.styles["Heading3"],
            fontSize=12,
            spaceAfter=6,
            spaceBefore=8,
            textColor=self.text_color,
            fontName="DejaVuSans",
        )

        # Professional body text style
        self.normal_style = ParagraphStyle(
            "FinancialNormal",
            parent=self.styles["Normal"],
            fontSize=10,
            fontName="DejaVuSans",
            spaceAfter=4,
            textColor=self.text_color,
            leading=12,
            leftIndent=5,
        )
        
        # Financial data style
        self.financial_data_style = ParagraphStyle(
            "FinancialData",
            parent=self.styles["Normal"],
            fontSize=9,
            fontName="DejaVuSans",
            spaceAfter=3,
            textColor=self.text_color,
            leading=11,
            rightIndent=10,
        )

        # Financial bold style
        self.bold_style = ParagraphStyle(
            "FinancialBold",
            parent=self.normal_style,
            fontSize=11,
            fontName="DejaVuSans",
            textColor=self.primary_color,
            spaceAfter=6,
        )
        
        # Currency style
        self.currency_style = ParagraphStyle(
            "Currency",
            parent=self.normal_style,
            fontSize=10,
            fontName="DejaVuSans",
            textColor=self.text_color,
            alignment=2,  # Right align
        )

        # Professional header/footer style
        self.header_style = ParagraphStyle(
            "FinancialHeader",
            parent=self.styles["Normal"],
            fontSize=9,
            fontName="DejaVuSans",
            textColor=self.medium_grey,
            alignment=2,
        )
        
        # Disclaimer style
        self.disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=self.styles["Normal"],
            fontSize=8,
            fontName="DejaVuSans",
            textColor=self.medium_grey,
            alignment=1,
            spaceAfter=5,
        )

    def generate_summary_pdf(self, summarized_data, output_path):
        try:
            # Setup professional document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=40,
                leftMargin=40,
                topMargin=60,
                bottomMargin=60,
            )
            story = []

            # Professional Cover Page
            cover_added = self._add_cover_page(story, summarized_data)
            if cover_added and len(story) > 2:  # Only add page break if we have content
                story.append(PageBreak())

            # Executive Summary
            exec_added = self._add_executive_summary(story, summarized_data)
            if exec_added and len(story) > 3:
                story.append(PageBreak())

            # Financial Statements
            if isinstance(summarized_data, dict):
                stmt_added = self._add_financial_statements(story, summarized_data)
                if stmt_added:
                    story.append(PageBreak())

                # Financial Analysis Charts
                charts_added = self._add_financial_charts(story, summarized_data)
                if charts_added:
                    story.append(PageBreak())

                # Key Financial Ratios
                ratios_added = self._add_financial_ratios(story, summarized_data)
                if ratios_added:
                    story.append(PageBreak())

            # Detailed Data Section (always add this as fallback)
            story.append(Paragraph("DETAILED FINANCIAL DATA", self.section_header_style))
            story.append(Spacer(1, 20))
            # Handle both possible field names and structures
            actual_data = summarized_data
            if isinstance(summarized_data, dict):
                # Check if we have the actual financial data structure
                if 'summerized_data' in summarized_data:
                    actual_data = summarized_data['summerized_data']
                elif 'summarized_data' in summarized_data:
                    actual_data = summarized_data['summarized_data']
            
            self._process_data_recursively(actual_data, story)

            # Professional Footer
            story.append(Spacer(1, 40))
            self._add_footer(story)

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
            return f"₾{amount/1000000:.1f}M"
        elif abs(amount) >= 1000:
            return f"₾{amount/1000:.1f}K"
        else:
            return f"₾{amount:,.0f}"

    def _add_cover_page(self, story, data):
        """Add professional cover page"""
        try:
            initial_length = len(story)
            
            # Company logo/header area
            story.append(Spacer(1, 50))
            
            # Main title
            story.append(Paragraph("FINANCIAL ANALYSIS REPORT", self.title_style))
            story.append(Spacer(1, 30))
            
            # Company name if available
            company_name = self._extract_company_name(data)
            if company_name and company_name != "Financial Analysis Subject":
                story.append(Paragraph(company_name, self.company_style))
                story.append(Spacer(1, 20))
            
            # Report period
            period = self._extract_reporting_period(data)
            if period:
                story.append(Paragraph(f"Reporting Period: {period}", self.subtitle_style))
                story.append(Spacer(1, 40))
            
            # Key highlights box - only if we have meaningful data
            highlights = self._extract_key_highlights(data)
            if highlights and len(highlights) > 1:  # More than just header
                story.append(Paragraph("EXECUTIVE HIGHLIGHTS", self.section_header_style))
                story.append(Spacer(1, 15))
                
                highlight_table = Table(highlights, colWidths=[2.5*inch, 2*inch, 1.5*inch])
                highlight_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
                    ('TEXTCOLOR', (0, 0), (-1, 0), white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), self.light_grey),
                    ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, self.medium_grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.light_grey]),
                ]))
                story.append(highlight_table)
                story.append(Spacer(1, 20))
            
            # Generation info
            story.append(Spacer(1, 60))
            current_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
            story.append(Paragraph(f"Generated on {current_date}", self.header_style))
            story.append(Paragraph("by NGL Financial Analysis System", self.header_style))
            
            # Return True if we added meaningful content
            return len(story) > initial_length + 3  # More than just basic title and dates
            
        except Exception as e:
            print(f"Error creating cover page: {e}")
            return False

    def _add_executive_summary(self, story, data):
        """Add executive summary with key metrics"""
        try:
            initial_length = len(story)
            
            # Financial overview
            content_added = False
            if isinstance(data, dict):
                overview_data = self._extract_financial_overview(data)
                if overview_data:
                    if not content_added:
                        story.append(Paragraph("EXECUTIVE SUMMARY", self.section_header_style))
                        story.append(Spacer(1, 20))
                        content_added = True
                    
                    story.append(Paragraph("Financial Overview", self.heading_style))
                    story.append(Spacer(1, 10))
                    
                    for item in overview_data:
                        story.append(Paragraph(f"• {item}", self.normal_style))
                    story.append(Spacer(1, 15))
            
            # Performance metrics table
            metrics = self._extract_performance_metrics(data)
            if metrics and len(metrics) > 1:  # More than just header
                if not content_added:
                    story.append(Paragraph("EXECUTIVE SUMMARY", self.section_header_style))
                    story.append(Spacer(1, 20))
                    content_added = True
                
                story.append(Paragraph("Key Performance Indicators", self.heading_style))
                story.append(Spacer(1, 10))
                
                metrics_table = Table(metrics, colWidths=[2.5*inch, 1.5*inch, 2*inch])
                metrics_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.blue_accent),
                    ('TEXTCOLOR', (0, 0), (-1, 0), white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), white),
                    ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, self.medium_grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(metrics_table)
            
            return content_added
            
        except Exception as e:
            print(f"Error creating executive summary: {e}")
            return False

    def _add_financial_statements(self, story, data):
        """Add formatted financial statements"""
        try:
            content_added = False
            
            # Income Statement
            income_statement = self._extract_income_statement(data)
            if income_statement and len(income_statement) > 1:
                if not content_added:
                    story.append(Paragraph("FINANCIAL STATEMENTS", self.section_header_style))
                    story.append(Spacer(1, 20))
                    content_added = True
                
                story.append(Paragraph("Income Statement", self.heading_style))
                story.append(Spacer(1, 10))
                
                income_table = Table(income_statement, colWidths=[3*inch, 1*inch, 1*inch, 1*inch])
                income_table.setStyle(self._get_financial_table_style())
                story.append(income_table)
                story.append(Spacer(1, 20))
            
            # Balance Sheet
            balance_sheet = self._extract_balance_sheet(data)
            if balance_sheet and len(balance_sheet) > 1:
                if not content_added:
                    story.append(Paragraph("FINANCIAL STATEMENTS", self.section_header_style))
                    story.append(Spacer(1, 20))
                    content_added = True
                
                story.append(Paragraph("Balance Sheet", self.heading_style))
                story.append(Spacer(1, 10))
                
                balance_table = Table(balance_sheet, colWidths=[3*inch, 1*inch, 1*inch, 1*inch])
                balance_table.setStyle(self._get_financial_table_style())
                story.append(balance_table)
                story.append(Spacer(1, 20))
            
            # Cash Flow Statement
            cash_flow = self._extract_cash_flow(data)
            if cash_flow and len(cash_flow) > 1:
                if not content_added:
                    story.append(Paragraph("FINANCIAL STATEMENTS", self.section_header_style))
                    story.append(Spacer(1, 20))
                    content_added = True
                
                story.append(Paragraph("Cash Flow Statement", self.heading_style))
                story.append(Spacer(1, 10))
                
                cf_table = Table(cash_flow, colWidths=[3*inch, 1*inch, 1*inch, 1*inch])
                cf_table.setStyle(self._get_financial_table_style())
                story.append(cf_table)
            
            return content_added
            
        except Exception as e:
            print(f"Error creating financial statements: {e}")
            return False

    def _add_financial_charts(self, story, data):
        """Add financial charts using matplotlib"""
        try:
            content_added = False
            
            # Revenue trend chart
            revenue_chart = self._create_revenue_chart(data)
            if revenue_chart:
                if not content_added:
                    story.append(Paragraph("FINANCIAL ANALYSIS CHARTS", self.section_header_style))
                    story.append(Spacer(1, 20))
                    content_added = True
                
                story.append(Paragraph("Revenue Trend Analysis", self.heading_style))
                story.append(Spacer(1, 10))
                story.append(revenue_chart)
                story.append(Spacer(1, 20))
            
            # Profitability chart
            profit_chart = self._create_profitability_chart(data)
            if profit_chart:
                if not content_added:
                    story.append(Paragraph("FINANCIAL ANALYSIS CHARTS", self.section_header_style))
                    story.append(Spacer(1, 20))
                    content_added = True
                
                story.append(Paragraph("Profitability Analysis", self.heading_style))
                story.append(Spacer(1, 10))
                story.append(profit_chart)
                story.append(Spacer(1, 20))
            
            return content_added
            
        except Exception as e:
            print(f"Error creating financial charts: {e}")
            return False

    def _add_financial_ratios(self, story, data):
        """Add calculated financial ratios"""
        try:
            content_added = False
            
            ratios = self._calculate_financial_ratios(data)
            if ratios:
                # Liquidity ratios
                if 'liquidity' in ratios and len(ratios['liquidity']) > 1:
                    if not content_added:
                        story.append(Paragraph("FINANCIAL RATIOS & ANALYSIS", self.section_header_style))
                        story.append(Spacer(1, 20))
                        content_added = True
                    
                    story.append(Paragraph("Liquidity Ratios", self.heading_style))
                    story.append(Spacer(1, 10))
                    
                    liquidity_table = Table(ratios['liquidity'], colWidths=[2.5*inch, 1.5*inch, 2*inch])
                    liquidity_table.setStyle(self._get_ratio_table_style())
                    story.append(liquidity_table)
                    story.append(Spacer(1, 15))
                
                # Profitability ratios
                if 'profitability' in ratios and len(ratios['profitability']) > 1:
                    if not content_added:
                        story.append(Paragraph("FINANCIAL RATIOS & ANALYSIS", self.section_header_style))
                        story.append(Spacer(1, 20))
                        content_added = True
                    
                    story.append(Paragraph("Profitability Ratios", self.heading_style))
                    story.append(Spacer(1, 10))
                    
                    profit_table = Table(ratios['profitability'], colWidths=[2.5*inch, 1.5*inch, 2*inch])
                    profit_table.setStyle(self._get_ratio_table_style())
                    story.append(profit_table)
                    story.append(Spacer(1, 15))
            
            return content_added
            
        except Exception as e:
            print(f"Error creating financial ratios: {e}")
            return False

    def _add_footer(self, story):
        """Add professional footer"""
        story.append(Spacer(1, 20))
        story.append(Paragraph(
            "This report contains confidential financial information and is intended for authorized recipients only.",
            self.disclaimer_style
        ))
        story.append(Paragraph(
            "Analysis based on available financial data and standard accounting principles.",
            self.disclaimer_style
        ))

    # Helper methods for data extraction and formatting
    
    def _get_financial_analysis(self, data):
        """Extract financial_analysis from various data structures"""
        if not isinstance(data, dict):
            return None
        
        # Direct access
        if 'financial_analysis' in data:
            return data['financial_analysis']
        
        # Inside summerized_data
        if 'summerized_data' in data and isinstance(data['summerized_data'], dict):
            if 'financial_analysis' in data['summerized_data']:
                return data['summerized_data']['financial_analysis']
        
        # Inside summarized_data (alternative spelling)
        if 'summarized_data' in data and isinstance(data['summarized_data'], dict):
            if 'financial_analysis' in data['summarized_data']:
                return data['summarized_data']['financial_analysis']
        
        return None
    
    def _extract_company_name(self, data):
        """Extract company name from data"""
        if isinstance(data, dict):
            # Check the main data structure first
            for key in ['company_name', 'company', 'business_name', 'entity_name']:
                if key in data and data[key]:
                    return str(data[key])
            
            # Check inside summerized_data if it exists
            if 'summerized_data' in data:
                inner_data = data['summerized_data']
                if isinstance(inner_data, dict):
                    for key in ['company_name', 'company', 'business_name', 'entity_name']:
                        if key in inner_data and inner_data[key]:
                            return str(inner_data[key])
            
            # Check inside financial_analysis if it exists
            if 'financial_analysis' in data:
                fa_data = data['financial_analysis']
                if isinstance(fa_data, dict):
                    for key in ['company_name', 'company', 'business_name', 'entity_name']:
                        if key in fa_data and fa_data[key]:
                            return str(fa_data[key])
        
        return "Financial Analysis Subject"

    def _extract_reporting_period(self, data):
        """Extract reporting period from data"""
        if isinstance(data, dict):
            for key in ['reporting_period', 'period', 'financial_period']:
                if key in data and data[key]:
                    return str(data[key])
            
            # Try to extract from financial analysis
            if 'financial_analysis' in data:
                fa = data['financial_analysis']
                if isinstance(fa, dict):
                    years = []
                    for section in ['income_statement', 'balance_sheet', 'cash_flow_statement']:
                        if section in fa and isinstance(fa[section], dict):
                            for item_key, item_value in fa[section].items():
                                if isinstance(item_value, dict):
                                    years.extend(item_value.keys())
                    
                    if years:
                        years = sorted(set(years))
                        if len(years) > 1:
                            return f"{years[0]} - {years[-1]}"
                        else:
                            return years[0]
        return datetime.now().strftime("%Y")

    def _extract_key_highlights(self, data):
        """Extract key highlights for cover page"""
        if not isinstance(data, dict):
            return None
            
        highlights = [["Metric", "Latest Period", "Status"]]
        
        # Try to extract key financial metrics
        fa = self._get_financial_analysis(data)
        if fa:
            # Revenue
            revenue = self._get_latest_value(fa, 'income_statement', 'revenue_sales')
            if revenue:
                highlights.append(["Total Revenue", self._format_currency(revenue), "✓"])
            
            # Net Income
            net_income = self._get_latest_value(fa, 'income_statement', 'net_income')
            if net_income:
                status = "✓" if net_income > 0 else "⚠"
                highlights.append(["Net Income", self._format_currency(net_income), status])
            
            # Cash Flow
            cash_flow = self._get_latest_value(fa, 'cash_flow_statement', 'cash_flow_from_operations')
            if cash_flow:
                status = "✓" if cash_flow > 0 else "⚠"
                highlights.append(["Operating Cash Flow", self._format_currency(cash_flow), status])
        
        return highlights if len(highlights) > 1 else None

    def _extract_financial_overview(self, data):
        """Extract financial overview points"""
        overview = []
        
        fa = self._get_financial_analysis(data)
        if fa:
            
            # Revenue analysis
            revenue_growth = self._calculate_growth_rate(fa, 'income_statement', 'revenue_sales')
            if revenue_growth is not None:
                trend = "increased" if revenue_growth > 0 else "decreased"
                overview.append(f"Revenue {trend} by {abs(revenue_growth):.1f}% compared to previous period")
            
            # Profitability analysis
            net_margin = self._calculate_net_margin(fa)
            if net_margin is not None:
                overview.append(f"Net profit margin of {net_margin:.1f}%")
            
            # Liquidity analysis
            current_ratio = self._calculate_current_ratio(fa)
            if current_ratio is not None:
                status = "strong" if current_ratio > 1.5 else "adequate" if current_ratio > 1 else "weak"
                overview.append(f"Current ratio of {current_ratio:.2f} indicates {status} liquidity")
        
        return overview if overview else None

    def _extract_performance_metrics(self, data):
        """Extract performance metrics for table"""
        fa = self._get_financial_analysis(data)
        if not fa:
            return None
        metrics = [["Metric", "Value", "Interpretation"]]
        
        # Revenue metrics
        revenue = self._get_latest_value(fa, 'income_statement', 'revenue_sales')
        if revenue:
            metrics.append(["Total Revenue", self._format_currency(revenue), "Primary income source"])
        
        # Profitability metrics
        gross_profit = self._get_latest_value(fa, 'income_statement', 'gross_profit')
        if gross_profit and revenue:
            gross_margin = (gross_profit / revenue) * 100
            metrics.append(["Gross Profit Margin", f"{gross_margin:.1f}%", self._interpret_margin(gross_margin)])
        
        # Efficiency metrics
        current_ratio = self._calculate_current_ratio(fa)
        if current_ratio:
            metrics.append(["Current Ratio", f"{current_ratio:.2f}", self._interpret_current_ratio(current_ratio)])
        
        return metrics if len(metrics) > 1 else None

    def _extract_income_statement(self, data):
        """Extract and format income statement"""
        fa = self._get_financial_analysis(data)
        if not fa:
            return None
        if 'income_statement' not in fa:
            return None
            
        is_data = fa['income_statement']
        
        # Get all years
        years = set()
        for item in is_data.values():
            if isinstance(item, dict):
                years.update(item.keys())
        years = sorted(years)
        
        if not years:
            return None
        
        # Build table
        table_data = [["Income Statement"] + years]
        
        # Define order of income statement items
        is_items = [
            ('revenue_sales', 'Revenue'),
            ('cogs', 'Cost of Goods Sold'),
            ('gross_profit', 'Gross Profit'),
            ('operating_expenses', 'Operating Expenses'),
            ('operating_profit_ebit', 'Operating Profit (EBIT)'),
            ('interest_expense', 'Interest Expense'),
            ('profit_before_tax_ebt', 'Profit Before Tax'),
            ('income_tax_expense', 'Income Tax'),
            ('net_income', 'Net Income'),
        ]
        
        for key, label in is_items:
            if key in is_data and isinstance(is_data[key], dict):
                row = [label]
                for year in years:
                    value = is_data[key].get(year, 0)
                    row.append(self._format_currency(value) if value else "-")
                table_data.append(row)
        
        return table_data if len(table_data) > 1 else None

    def _extract_balance_sheet(self, data):
        """Extract and format balance sheet"""
        fa = self._get_financial_analysis(data)
        if not fa:
            return None
        if 'balance_sheet' not in fa:
            return None
            
        bs_data = fa['balance_sheet']
        
        # Get all years
        years = set()
        for item in bs_data.values():
            if isinstance(item, dict):
                years.update(item.keys())
        years = sorted(years)
        
        if not years:
            return None
        
        # Build table
        table_data = [["Balance Sheet"] + years]
        
        # Assets
        table_data.append(["ASSETS", ""] + [""] * (len(years) - 1))
        
        asset_items = [
            ('cash_equivalents', 'Cash & Equivalents'),
            ('accounts_receivable', 'Accounts Receivable'),
            ('inventory', 'Inventory'),
            ('other_current_assets', 'Other Current Assets'),
            ('ppe', 'Property, Plant & Equipment'),
            ('intangible_assets', 'Intangible Assets'),
        ]
        
        for key, label in asset_items:
            if key in bs_data and isinstance(bs_data[key], dict):
                row = [f"  {label}"]
                for year in years:
                    value = bs_data[key].get(year, 0)
                    row.append(self._format_currency(value) if value else "-")
                table_data.append(row)
        
        # Liabilities & Equity
        table_data.append(["LIABILITIES & EQUITY", ""] + [""] * (len(years) - 1))
        
        liability_items = [
            ('accounts_payable', 'Accounts Payable'),
            ('short_term_debt', 'Short-term Debt'),
            ('long_term_debt', 'Long-term Debt'),
            ('shareholders_equity', 'Shareholders Equity'),
        ]
        
        for key, label in liability_items:
            if key in bs_data and isinstance(bs_data[key], dict):
                row = [f"  {label}"]
                for year in years:
                    value = bs_data[key].get(year, 0)
                    row.append(self._format_currency(value) if value else "-")
                table_data.append(row)
        
        return table_data if len(table_data) > 1 else None

    def _extract_cash_flow(self, data):
        """Extract and format cash flow statement"""
        fa = self._get_financial_analysis(data)
        if not fa:
            return None
        if 'cash_flow_statement' not in fa:
            return None
            
        cf_data = fa['cash_flow_statement']
        
        # Get all years
        years = set()
        for item in cf_data.values():
            if isinstance(item, dict):
                years.update(item.keys())
        years = sorted(years)
        
        if not years:
            return None
        
        # Build table
        table_data = [["Cash Flow Statement"] + years]
        
        cf_items = [
            ('cash_flow_from_operations', 'Operating Cash Flow'),
            ('capital_expenditures', 'Capital Expenditures'),
            ('free_cash_flow', 'Free Cash Flow'),
            ('changes_in_working_capital', 'Working Capital Changes'),
            ('interest_paid', 'Interest Paid'),
            ('taxes_paid', 'Taxes Paid'),
        ]
        
        for key, label in cf_items:
            if key in cf_data and isinstance(cf_data[key], dict):
                row = [label]
                for year in years:
                    value = cf_data[key].get(year, 0)
                    row.append(self._format_currency(value) if value else "-")
                table_data.append(row)
        
        return table_data if len(table_data) > 1 else None

    def _get_financial_table_style(self):
        """Get table style for financial statements"""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), white),
            ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, self.medium_grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.light_grey]),
        ])

    def _get_ratio_table_style(self):
        """Get table style for financial ratios"""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.blue_accent),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), white),
            ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, self.medium_grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ])

    # Financial calculation methods
    
    def _get_latest_value(self, fa, section, item):
        """Get the latest value for a financial item"""
        if section not in fa or item not in fa[section]:
            return None
        
        item_data = fa[section][item]
        if not isinstance(item_data, dict):
            return None
        
        years = sorted(item_data.keys())
        if not years:
            return None
        
        latest_year = years[-1]
        value = item_data[latest_year]
        return float(value) if value and str(value).replace('.', '').replace('-', '').isdigit() else None

    def _calculate_growth_rate(self, fa, section, item):
        """Calculate growth rate between latest two periods"""
        if section not in fa or item not in fa[section]:
            return None
        
        item_data = fa[section][item]
        if not isinstance(item_data, dict):
            return None
        
        years = sorted(item_data.keys())
        if len(years) < 2:
            return None
        
        current = item_data.get(years[-1])
        previous = item_data.get(years[-2])
        
        if not current or not previous:
            return None
        
        try:
            current = float(current)
            previous = float(previous)
            if previous != 0:
                return ((current - previous) / previous) * 100
        except (ValueError, TypeError):
            pass
        
        return None

    def _calculate_net_margin(self, fa):
        """Calculate net profit margin"""
        revenue = self._get_latest_value(fa, 'income_statement', 'revenue_sales')
        net_income = self._get_latest_value(fa, 'income_statement', 'net_income')
        
        if revenue and net_income and revenue != 0:
            return (net_income / revenue) * 100
        return None

    def _calculate_current_ratio(self, fa):
        """Calculate current ratio"""
        # Current assets approximation
        cash = self._get_latest_value(fa, 'balance_sheet', 'cash_equivalents') or 0
        ar = self._get_latest_value(fa, 'balance_sheet', 'accounts_receivable') or 0
        inventory = self._get_latest_value(fa, 'balance_sheet', 'inventory') or 0
        other_current = self._get_latest_value(fa, 'balance_sheet', 'other_current_assets') or 0
        
        current_assets = cash + ar + inventory + other_current
        
        # Current liabilities approximation
        ap = self._get_latest_value(fa, 'balance_sheet', 'accounts_payable') or 0
        short_debt = self._get_latest_value(fa, 'balance_sheet', 'short_term_debt') or 0
        
        current_liabilities = ap + short_debt
        
        if current_liabilities != 0:
            return current_assets / current_liabilities
        return None

    def _calculate_financial_ratios(self, data):
        """Calculate comprehensive financial ratios"""
        fa = self._get_financial_analysis(data)
        if not fa:
            return None
        ratios = {}
        
        # Liquidity ratios
        liquidity = [["Ratio", "Value", "Benchmark"]]
        
        current_ratio = self._calculate_current_ratio(fa)
        if current_ratio:
            benchmark = "Good (>1.5)" if current_ratio > 1.5 else "Fair (1.0-1.5)" if current_ratio > 1 else "Poor (<1.0)"
            liquidity.append(["Current Ratio", f"{current_ratio:.2f}", benchmark])
        
        if len(liquidity) > 1:
            ratios['liquidity'] = liquidity
        
        # Profitability ratios
        profitability = [["Ratio", "Value", "Analysis"]]
        
        net_margin = self._calculate_net_margin(fa)
        if net_margin:
            analysis = "Excellent (>10%)" if net_margin > 10 else "Good (5-10%)" if net_margin > 5 else "Needs Improvement (<5%)"
            profitability.append(["Net Profit Margin", f"{net_margin:.1f}%", analysis])
        
        # Gross margin
        revenue = self._get_latest_value(fa, 'income_statement', 'revenue_sales')
        gross_profit = self._get_latest_value(fa, 'income_statement', 'gross_profit')
        if revenue and gross_profit:
            gross_margin = (gross_profit / revenue) * 100
            analysis = "Strong (>50%)" if gross_margin > 50 else "Moderate (20-50%)" if gross_margin > 20 else "Low (<20%)"
            profitability.append(["Gross Profit Margin", f"{gross_margin:.1f}%", analysis])
        
        if len(profitability) > 1:
            ratios['profitability'] = profitability
        
        return ratios if ratios else None

    def _create_revenue_chart(self, data):
        """Create revenue trend chart using matplotlib"""
        fa = self._get_financial_analysis(data)
        if not fa:
            return None
        if 'income_statement' not in fa or 'revenue_sales' not in fa['income_statement']:
            return None
        
        revenue_data = fa['income_statement']['revenue_sales']
        if not isinstance(revenue_data, dict):
            return None
        
        years = sorted(revenue_data.keys())
        values = [float(revenue_data[year]) for year in years if revenue_data[year]]
        
        if len(years) < 2:
            return None
        
        try:
            # Create matplotlib chart
            plt.style.use('default')
            fig, ax = plt.subplots(figsize=(8, 5))
            
            # Plot data
            bars = ax.bar(years, values, color='#3b82f6', alpha=0.8, edgecolor='#1e40af', linewidth=1)
            
            # Formatting
            ax.set_title('Revenue Trend Analysis', fontsize=14, fontweight='bold', pad=20)
            ax.set_xlabel('Year', fontsize=12)
            ax.set_ylabel('Revenue (₾)', fontsize=12)
            
            # Format y-axis
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₾{x/1000000:.1f}M' if x >= 1000000 else f'₾{x/1000:.0f}K'))
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.01,
                       f'₾{value/1000000:.1f}M' if value >= 1000000 else f'₾{value/1000:.0f}K',
                       ha='center', va='bottom', fontsize=10)
            
            # Grid and styling
            ax.grid(True, alpha=0.3)
            ax.set_axisbelow(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save to memory
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()
            
            # Create ReportLab Image
            image = Image(img_buffer, width=6*inch, height=3.75*inch)
            return image
            
        except Exception as e:
            print(f"Error creating revenue chart: {e}")
            return None

    def _create_profitability_chart(self, data):
        """Create profitability analysis chart"""
        fa = self._get_financial_analysis(data)
        if not fa:
            return None
        is_data = fa.get('income_statement', {})
        
        # Get data for latest year
        years = set()
        for item in is_data.values():
            if isinstance(item, dict):
                years.update(item.keys())
        
        if not years:
            return None
        
        latest_year = sorted(years)[-1]
        
        # Extract profitability metrics
        revenue = self._get_value_for_year(is_data, 'revenue_sales', latest_year)
        gross_profit = self._get_value_for_year(is_data, 'gross_profit', latest_year)
        operating_profit = self._get_value_for_year(is_data, 'operating_profit_ebit', latest_year)
        net_income = self._get_value_for_year(is_data, 'net_income', latest_year)
        
        if not revenue or revenue <= 0:
            return None
        
        try:
            # Calculate margins
            margins = []
            labels = []
            
            if gross_profit is not None:
                margins.append((gross_profit / revenue) * 100)
                labels.append('Gross Margin')
            
            if operating_profit is not None:
                margins.append((operating_profit / revenue) * 100)
                labels.append('Operating Margin')
            
            if net_income is not None:
                margins.append((net_income / revenue) * 100)
                labels.append('Net Margin')
            
            if not margins:
                return None
            
            # Create chart
            fig, ax = plt.subplots(figsize=(8, 5))
            
            # Color coding
            colors = ['#10b981', '#3b82f6', '#8b5cf6'][:len(margins)]
            
            bars = ax.bar(labels, margins, color=colors, alpha=0.8, edgecolor='white', linewidth=2)
            
            # Formatting
            ax.set_title(f'Profitability Analysis - {latest_year}', fontsize=14, fontweight='bold', pad=20)
            ax.set_ylabel('Margin (%)', fontsize=12)
            ax.set_ylim(0, max(margins) * 1.2 if margins else 100)
            
            # Add value labels
            for bar, margin in zip(bars, margins):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                       f'{margin:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')
            
            # Grid and styling
            ax.grid(True, alpha=0.3, axis='y')
            ax.set_axisbelow(True)
            plt.tight_layout()
            
            # Save to memory
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()
            
            # Create ReportLab Image
            image = Image(img_buffer, width=6*inch, height=3.75*inch)
            return image
            
        except Exception as e:
            print(f"Error creating profitability chart: {e}")
            return None

    def _get_value_for_year(self, section_data, item, year):
        """Get value for specific year from section data"""
        if item not in section_data:
            return None
        
        item_data = section_data[item]
        if not isinstance(item_data, dict):
            return None
        
        value = item_data.get(year)
        if value is None:
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _interpret_margin(self, margin):
        """Interpret margin levels"""
        if margin > 50:
            return "Excellent"
        elif margin > 30:
            return "Very Good"
        elif margin > 15:
            return "Good"
        elif margin > 5:
            return "Fair"
        else:
            return "Needs Improvement"

    def _interpret_current_ratio(self, ratio):
        """Interpret current ratio"""
        if ratio > 2:
            return "Very Strong Liquidity"
        elif ratio > 1.5:
            return "Strong Liquidity"
        elif ratio > 1:
            return "Adequate Liquidity"
        else:
            return "Weak Liquidity"
