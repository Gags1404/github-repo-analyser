import os
from app import app

if __name__ == '__main__':
    # Set Flask environment variables
    os.environ['FLASK_APP'] = 'app.py'
    os.environ['FLASK_ENV'] = 'development'
    
    # Set GitHub token for API requests (add your token here if needed)
    os.environ['GITHUB_TOKEN'] = "" # Replace with your actual token when needed
    
    # Run the Flask application
    app.run(debug=True, host='0.0.0.0', port=5000)
