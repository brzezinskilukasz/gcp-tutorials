"""Main application file for Hello Game Backend."""

import atexit
import logging
import os
import sys
import threading
import time

from flask import Flask, request
from flask_cors import CORS
from sqlalchemy import text

# Add current directory to Python path for local imports
sys.path.append(os.path.dirname(__file__))

from config import Config, config
from models import db, GameSubmission


def setup_logging():
    """Setup logging configuration."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
def create_app(config_name='default'):
    """Application factory pattern."""

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting app in %s configuration.", config_name)

    app = Flask(__name__)
    cfg = config[config_name]
    app.config.from_object(cfg)

    # Get DB connection from Config.get_connection_settings()
    sqlalchemy_uri, engine_options, connector = cfg.get_connection_settings()

    # Apply URI required by Flask-SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = sqlalchemy_uri

    # Initialize Flask-SQLAlchemy engine with custom options
    # (creator function for Cloud SQL Connector or default for local dev)
    db._engine_options = engine_options
    db.init_app(app)

    CORS(app)  # TODO: Enable CORS for specific origins in production

    # --- Close connector on app teardown (if used) ---
    def close_connector(exception=None):
        """Cloud SQL Connector cleanup function."""
        logger.info("Application is shutting down...")
        logger.info("Closing Cloud SQL Connector...")
        try:
            connector.close()
            logger.info("Cloud SQL Connector closed successfully.")
        except Exception as e:
            logger.error("Error closing Cloud SQL Connector: %s", e)

    # --- Periodic DB Health Check ---
    def start_db_connection_health_check(engine, interval_seconds: int = 30):
        """
        Periodically checks database connectivity using the provided SQLAlchemy engine.
        Runs in a daemon thread so it never blocks app startup.

        NOTE: This is for TUTORIAL PURPOSES ONLY.
        In a real production app, use external health probes (e.g., Cloud Run startup probe).
        We use this here to generate visible logs so you can see the connection go from
        FAILED to SUCCESS as you apply IAM permissions.

        :param engine: SQLAlchemy engine instance used for DB connections.
        :param interval_seconds: How often to run the health check.
        """
        def _probe():
            # A little delay so that the app is ready before probing starts
            time.sleep(10)

            while True:
                try:
                    with engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    logger.info("DB Health Check: SUCCESS - connection established.")
                except Exception as e:
                    error = str(e).split("\n")[0] # trim to only first line
                    logger.error("DB Health Check: FAILED - %s", error)

                time.sleep(interval_seconds)

        thread = threading.Thread(target=_probe, daemon=True)
        thread.start()
        logger.info("Periodic DB health check thread started")

    # Start period DB Health probe
    with app.app_context():
        engine = db.get_engine()
    start_db_connection_health_check(engine=engine)

    if connector:
        atexit.register(lambda: close_connector())

    return app

environment = os.getenv('ENVIRONMENT', 'development')
app = create_app(environment)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - tests database connectivity."""
    try:
        # Test database connection using SQLAlchemy 2.0+ syntax
        db.session.execute(text('SELECT 1'))
        logging.info("Database connection successful.")
        return {"status": "healthy", "database": "connected"}, 200
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        logging.error(f"DB Connection Info: {app.config['SQLALCHEMY_DATABASE_URI']}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}, 500

@app.route('/migrate', methods=['POST'])
def migrate():
    """
    Create database tables.

    WARNING: This endpoint is for development/tutorial purposes only.
    In production, use proper migration tools like Flask-Migrate or Alembic.
    This endpoint should be removed or protected in production environments.
    """
    try:
        logging.info("Starting database migration...")
        db.create_all()
        logging.info("Database migration completed.")
        return {"status": "success", "message": "Database tables created"}, 200
    except Exception as e:
        logging.error(f"Database migration failed: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get game statistics from database."""
    try:
        # Get stats from database
        stats = GameSubmission.get_name_stats()
        logging.info("Retrieved stats from database successfully.")
        return stats, 200
    except Exception as e:
        # Fallback to mock data if database unavailable
        logging.error(f"Failed to retrieve stats from database: {e}")
        logging.error("Returning mock data instead.")
        mock_name_data = [
            {"name": "Alex", "count": 10},
            {"name": "Sarah", "count": 25},
            {"name": "Mike", "count": 6},
            {"name": "Emma", "count": 12},
            {"name": "John", "count": 15},
            {"name": "Lisa", "count": 7}
        ]

        return {
            "total_players": 75,
            "unique_names": 6,
            "most_popular": "Sarah",
            "name_data": mock_name_data,
            "database_error": str(e)
        }, 200

@app.route('/submit', methods=['POST'])
def submit_name():
    """Submit a new name to the database."""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return {"error": "Name is required"}, 400

        name = data['name']
        if not name.strip():
            return {"error": "Name cannot be empty"}, 400

        submission = GameSubmission.add_submission(name)
        return {
            "status": "success",
            "message": f"Name '{submission.name}' submitted successfully",
            "submission": submission.to_dict()
        }, 201

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
