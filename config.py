import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class."""
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-for-github-analyzer')
    DEBUG = False
    TESTING = False
    
    # Database configuration
    # Using file-based SQLite database in the project root
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///github_analyzer.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # GitHub API configuration
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
    GITHUB_API_URL = 'https://api.github.com'
    
    # Application settings
    RESULTS_PER_PAGE = 10
    CACHE_TIMEOUT = 3600  # 1 hour in seconds


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_github_analyzer.db'


class ProductionConfig(Config):
    """Production configuration."""
    # Production-specific settings
    DEBUG = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Get configuration based on environment
def get_config():
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, config['default'])
