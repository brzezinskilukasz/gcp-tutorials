"""Configuration settings for the Hello Game backend."""

import os
import logging
from google.cloud.sql.connector import Connector, IPTypes


logger = logging.getLogger(__name__)


class Config:
    """Base configuration class."""
    # pylint: disable=too-few-public-methods

    # DB settings (fallback for local development)
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'hello_game')
    DB_USER = os.getenv('DB_USER', 'hello_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'hello_password')

    # Used only in Cloud Run
    INSTANCE_CONNECTION_NAME = os.getenv('INSTANCE_CONNECTION_NAME')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def get_connection_settings():
        """
        Returns:
          (sqlalchemy_uri, engine_options, connector)
        """

        # --- Cloud SQL (production) with IAM Auth ---
        if Config.INSTANCE_CONNECTION_NAME:
            logger.info("Using Cloud SQL Python Connector (IAM Auth) for database connections.")
            connector = Connector()
            instance_name = Config.INSTANCE_CONNECTION_NAME

            def get_connection():
                logger.info("Establishing new connection using Cloud SQL Python Connector.")
                return connector.connect(
                    instance_connection_string=instance_name,
                    driver="pg8000",
                    user=Config.DB_USER,
                    db=Config.DB_NAME,
                    enable_iam_auth=True,     # IAM-based passwordless auth
                    ip_type=IPTypes.PRIVATE,  # PRIVATE or PUBLIC
                )

            # Dummy DB URI for SQLAlchemy
            sqlalchemy_uri = "postgresql+pg8000://"

            engine_options = {
                "creator": get_connection,
                "pool_size": 5,
                "max_overflow": 2,
                "pool_timeout": 30,
            }

            return sqlalchemy_uri, engine_options, connector

        # --- Local development with classic password-based connection ---
        logger.info("Using classic database connection (username/password) for local development.")
        sqlalchemy_uri = (
            f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}"
            f"@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
        )

        engine_options = {} # SQLAlchemy default options
        connector = None    # No Cloud SQL Connector in local mode

        return sqlalchemy_uri, engine_options, connector


class DevelopmentConfig(Config):
    """Development configuration."""
    # pylint: disable=too-few-public-methods
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    # pylint: disable=too-few-public-methods
    DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY')  # Must be set in production


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
