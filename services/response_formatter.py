import os
from flask import jsonify

class ResponseFormatter:
    @staticmethod
    def success_response(data=None, message="success", **kwargs):
        response = {
            "success": True,
            "message": message
        }
        
        if data is not None:
            response["data"] = data
        
        response.update(kwargs)
        return jsonify(response), 200
    
    @staticmethod
    def format_evaluation_response(filename, text_length, financial_analysis, pdf_result=None):
        response_data = {
            "message": "success",
            "filename": filename,
            "length": text_length,
        }
        
        if financial_analysis and financial_analysis.get("success"):
            response_data["success"] = True
            response_data["data"] = {
                "financial_analysis": {
                    "data": financial_analysis.get("data", financial_analysis),
                    "success": True
                }
            }
            
            response_data["pdf"] = ResponseFormatter._format_pdf_info(
                financial_analysis.get("pdf_result") or pdf_result
            )
        else:
            response_data["success"] = False
            error_message = "Gemini API not configured. Please set GEMINI_API_KEY environment variable."
            if financial_analysis and financial_analysis.get("error"):
                error_message = financial_analysis["error"]
            
            response_data["data"] = {
                "financial_analysis": {
                    "error": error_message
                }
            }
            response_data["pdf"] = {
                "available": False,
                "error": "Analysis failed"
            }
        
        return jsonify(response_data), 200
    
    @staticmethod
    def _format_pdf_info(pdf_result):
        if not pdf_result:
            return {
                "available": False,
                "error": "No PDF generation attempted"
            }
        
        if pdf_result.get("success"):
            filename = os.path.basename(pdf_result["file_path"])
            return {
                "available": True,
                "filename": filename,
                "url": pdf_result.get("public_url", f"/pdfs/{filename}")
            }
        else:
            return {
                "available": False,
                "error": pdf_result.get("error", "PDF generation failed")
            }
