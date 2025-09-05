import os
from flask import jsonify


class ResponseFormatter:
    @staticmethod
    def success_response(data=None, message="success", **kwargs):
        response = {"success": True, "message": message}

        if data is not None:
            response["data"] = data

        response.update(kwargs)
        return jsonify(response), 200

    @staticmethod
    def format_evaluation_response(
        filename,
        text_length,
        financial_analysis,
        pdf_result=None,
        file_count=1,
        processed_files=None,
    ):
        response_data = {
            "message": "success",
            "filename": filename,
            "length": text_length,
            "file_count": file_count,
        }

        if processed_files:
            response_data["processed_files"] = processed_files

        if financial_analysis and financial_analysis.get("success"):
            response_data["success"] = True
            full_data = financial_analysis.get("data", financial_analysis)
            response_data["data"] = {
                "financial_analysis": {"data": full_data, "success": True}
            }

            response_data["pdf"] = ResponseFormatter._format_pdf_info(
                financial_analysis.get("pdf_result") or pdf_result
            )
        else:
            response_data["success"] = False
            error_message = "Gemini API not configured. Please set GEMINI_API_KEY environment variable."
            if financial_analysis and financial_analysis.get("error"):
                error_message = financial_analysis["error"]

            response_data["data"] = {"financial_analysis": {"error": error_message}}
            response_data["pdf"] = {"available": False, "error": "Analysis failed"}

        return jsonify(response_data), 200

    @staticmethod
    def format_investment_response(
        filename, text_length, investment_analysis, file_count=1, processed_files=None
    ):
        response_data = {
            "message": "success",
            "filename": filename,
            "length": text_length,
            "file_count": file_count,
        }

        if processed_files:
            response_data["processed_files"] = processed_files

        if investment_analysis and investment_analysis.get("success"):
            response_data["success"] = True
            response_data["data"] = {
                "investment_analysis": {
                    "data": investment_analysis.get("data", investment_analysis),
                    "success": True,
                }
            }
        else:
            response_data["success"] = False
            error_message = "Gemini API not configured. Please set GEMINI_API_KEY environment variable."
            if investment_analysis and investment_analysis.get("error"):
                error_message = investment_analysis["error"]

            response_data["data"] = {"investment_analysis": {"error": error_message}}

        return jsonify(response_data), 200

    @staticmethod
    def format_sufficiency_response(sufficiency_result):
        if sufficiency_result.get("success"):
            response_data = {
                "success": True,
                "message": "Sufficiency check completed",
                "data": {
                    "sufficiency_percentage": sufficiency_result.get(
                        "sufficiency_percentage", 0
                    ),
                    "missing_data": sufficiency_result.get("missing_data", []),
                    "recommendations": sufficiency_result.get("recommendations", []),
                    "critical_gaps": sufficiency_result.get("critical_gaps", []),
                },
            }
        else:
            response_data = {
                "success": False,
                "message": "Sufficiency check failed",
                "error": sufficiency_result.get("error", "Unknown error occurred"),
            }

        return jsonify(response_data), 200

    @staticmethod
    def format_validity_response(validity_result):
        if validity_result.get("success"):
            response_data = {
                "success": True,
                "message": "Investment validity calculation completed",
                "data": validity_result.get("data", {}),
            }
        else:
            response_data = {
                "success": False,
                "message": "Investment validity calculation failed",
                "error": validity_result.get("error", "Unknown error occurred"),
            }

        return jsonify(response_data), 200

    @staticmethod
    def format_investor_response(investor_result):
        if investor_result.get("success"):
            response_data = {
                "success": True,
                "message": "Investor search completed",
                "data": investor_result.get("data", {}),
            }
        else:
            response_data = {
                "success": False,
                "message": "Investor search failed",
                "error": investor_result.get("error", "Unknown error occurred"),
            }

        return jsonify(response_data), 200

    @staticmethod
    def format_startup_response(startup_result):
        if startup_result.get("success"):
            response_data = {
                "success": True,
                "message": "Startup analysis completed",
                "data": startup_result.get("data", {}),
            }
        else:
            response_data = {
                "success": False,
                "message": "Startup analysis failed",
                "error": startup_result.get("error", "Unknown error occurred"),
            }

        return jsonify(response_data), 200

    @staticmethod
    def _format_pdf_info(pdf_result):
        if not pdf_result:
            return {"available": False, "error": "No PDF generation attempted"}

        if pdf_result.get("success"):
            filename = os.path.basename(pdf_result["file_path"])
            return {
                "available": True,
                "filename": filename,
                "url": pdf_result.get("public_url", f"/pdfs/{filename}"),
            }
        else:
            return {
                "available": False,
                "error": pdf_result.get("error", "PDF generation failed"),
            }
