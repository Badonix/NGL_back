from flask import Flask, jsonify
from flask_cors import CORS
import logging
from config import Config
from routes.evaluation import evaluation_bp
from routes.pdf import pdf_bp
from routes.valuation import valuation_bp
from routes.investment import investment_bp
from routes.loan import loan_bp
from routes.startup import startup_bp
from routes.competitor import competitor_bp
from routes.sec_lookup import sec_lookup_bp


def create_app():
    app = Flask(__name__)

    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH
    app.config["JSON_SORT_KEYS"] = False

    CORS(
        app,
        origins="*",
        methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    logging.basicConfig(level=logging.INFO)

    Config.ensure_directories()

    app.register_blueprint(evaluation_bp)
    app.register_blueprint(pdf_bp)
    app.register_blueprint(valuation_bp)
    app.register_blueprint(investment_bp)
    app.register_blueprint(loan_bp)
    app.register_blueprint(startup_bp)
    app.register_blueprint(competitor_bp)
    app.register_blueprint(sec_lookup_bp)

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for chat agents"""
        return jsonify({
            'status': 'healthy',
            'message': 'NGL Financial API is running',
            'version': '1.0.0'
        })

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=Config.FLASK_DEBUG, host=Config.FLASK_HOST, port=Config.FLASK_PORT)
