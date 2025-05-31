import os

# Set environment variables for testing
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_ENV'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite:///test_github_analyzer.db'
os.environ['SECRET_KEY'] = 'test_secret_key'
# GitHub token for API requests (add your token here if needed)
os.environ['GITHUB_TOKEN'] = 'test_github_token'
os.environ['CACHE_TIMEOUT'] = '3600'
