import os
import secrets
import subprocess
import sys
from pathlib import Path

def setup_environment():
    """Set up the development environment for the GitHub Repository Analyzer."""
    print("Setting up GitHub Repository Analyzer development environment...")
    
    # Create virtual environment if it doesn't exist
    if not os.path.exists("venv"):
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    
    # Determine the activate script based on OS
    if sys.platform == "win32":
        activate_script = os.path.join("venv", "Scripts", "activate")
        activate_cmd = f"{activate_script} && "
    else:
        activate_script = os.path.join("venv", "bin", "activate")
        activate_cmd = f"source {activate_script} && "
    
    # Install dependencies
    print("Installing dependencies...")
    if sys.platform == "win32":
        subprocess.run(f"{activate_cmd} pip install -r requirements.txt", shell=True, check=True)
    else:
        subprocess.run(["bash", "-c", f"{activate_cmd} pip install -r requirements.txt"], check=True)
    
    # Create .env file if it doesn't exist
    if not os.path.exists(".env"):
        print("Creating .env file...")
        with open(".env.example", "r") as example_file:
            env_content = example_file.read()
        
        # Generate a random secret key
        secret_key = secrets.token_hex(16)
        env_content = env_content.replace("your_secure_random_key_here", secret_key)
        
        with open(".env", "w") as env_file:
            env_file.write(env_content)
    
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    if not data_dir.exists():
        print("Creating data directory...")
        data_dir.mkdir()
    
    # Create static/images directory if it doesn't exist
    images_dir = Path("static/images")
    if not images_dir.exists():
        print("Creating images directory...")
        images_dir.mkdir(parents=True, exist_ok=True)
    
    print("\nSetup complete! You can now run the application with:")
    if sys.platform == "win32":
        print("venv\\Scripts\\activate && flask run")
    else:
        print("source venv/bin/activate && flask run")
    print("\nOr use Docker:")
    print("docker-compose up -d")

if __name__ == "__main__":
    setup_environment()
