import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from app.config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from app.errors import register_error_handlers
from app.routes.auth import auth_bp
from app.routes.documents import documents_bp
from app.routes.evidence import evidence_bp
from app.routes.extraction import extraction_bp
from app.routes.health import health_bp
from app.routes.qa import qa_bp
from app.routes.retrieval import retrieval_bp
from app.routes.trust import trust_bp

# Load .env if present
load_dotenv()


def create_app(config_class: type[Config] | None = None) -> Flask:
    """Application factory for ClarityKit backend."""
    app = Flask(__name__)

    if config_class is None:
        env = os.getenv("FLASK_ENV", "development").lower()
        if env == "production":
            config_class = ProductionConfig
        elif env == "testing":
            config_class = TestingConfig
        else:
            config_class = DevelopmentConfig

    app.config.from_object(config_class)

    # Restrictive CORS configuration
    allowed_origins = app.config.get("ALLOWED_ORIGINS", [])
    CORS(app, origins=allowed_origins)

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(retrieval_bp)
    app.register_blueprint(extraction_bp)
    app.register_blueprint(evidence_bp)
    app.register_blueprint(trust_bp)
    app.register_blueprint(qa_bp)

    return app
