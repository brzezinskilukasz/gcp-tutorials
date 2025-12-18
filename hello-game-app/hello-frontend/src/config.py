"""Configuration settings for the Hello Game frontend."""

import os


class Config:
    """Base configuration class."""
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'supersecret')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    PUBSUB_TOPIC_ID = 'hello-game-names'
    GOOGLE_CLOUD_PROJECT = 'hello-game-local'
    BACKEND_URL = 'http://localhost:8081'

    # Use Pub/Sub emulator for local development
    USE_PUBSUB_EMULATOR = True
    PUBSUB_EMULATOR_HOST = 'localhost:8085'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    BACKEND_URL = os.getenv('BACKEND_URL') # Hello Game Backend URL - must be set in production
    GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')  # GCP Project ID - this should be available in GCP env
    PUBSUB_TOPIC_ID = os.getenv('PUBSUB_TOPIC_ID')  # Topic ID - must be set in production
    
    USE_PUBSUB_EMULATOR = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}