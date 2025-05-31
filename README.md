# GitHub Repository Analyzer

A web application that analyzes public GitHub repositories, providing insights into repository metadata, contributors, commit activity, and language breakdown.

![GitHub Repository Analyzer](https://via.placeholder.com/1200x600/0d6efd/FFFFFF?text=GitHub+Repository+Analyzer)

## Features

- **Repository Analysis**: Fetch and display metadata for any public GitHub repository
- **Contributor Insights**: View top contributors and their contributions
- **Commit History**: Analyze recent commits and commit frequency over time
- **Language Breakdown**: Visualize the programming languages used in the repository
- **Responsive Design**: Mobile-friendly interface using Bootstrap 5
- **Data Visualization**: Interactive charts with Chart.js
- **Caching System**: SQLite database to minimize API calls and improve performance
- **API Integration**: GitHub REST API v3 with rate limiting awareness
- **Docker Support**: Easy deployment with Docker and docker-compose

## Getting Started

### Prerequisites

- Python 3.9+
- pip (Python package manager)
- Git
- Docker and docker-compose (optional, for containerized deployment)

### Installation

#### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/Gags1404/github-repo-analyser.git
   cd github-repo-analyser
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following variables:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   DATABASE_URL=sqlite:///github_repos.db
   SECRET_KEY=your_secret_key_here
   GITHUB_TOKEN=your_github_personal_access_token  # Optional but recommended
   ```

5. Initialize the database:
   ```bash
   flask db init  # If using Flask-Migrate
   ```

6. Run the application:
   ```bash
   flask run
   ```

7. Open your browser and navigate to `http://localhost:5000`

#### Docker Deployment (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/Gags1404/github-repo-analyser.git
   cd github-repo-analyser
   ```

2. Create a `.env` file from the example:
   ```bash
   # On Linux/macOS
   cp .env.example .env
   # On Windows
   copy .env.example .env
   ```

3. Edit the `.env` file to set your GitHub token and other configuration options:
   ```
   GITHUB_TOKEN=your_github_personal_access_token
   SECRET_KEY=your_secure_random_key_here
   ```

   > **Important**: The GitHub token is required to avoid API rate limiting. You can create one at [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens). The token only needs `public_repo` scope for analyzing public repositories.

4. For development mode (without Nginx):
   ```bash
   # On Windows
   .\docker-run.ps1 -mode dev -build
   # On Linux/macOS
   docker-compose up -d
   ```

5. For production mode (with Nginx as reverse proxy):
   ```bash
   # On Windows
   .\docker-run.ps1 -mode prod -build
   # On Linux/macOS
   docker-compose --profile prod up -d
   ```

6. Access the application:
   - Development mode: `http://localhost:5000`
   - Production mode: `https://localhost` (requires SSL certificates)

7. To generate self-signed SSL certificates for HTTPS in development:
   ```bash
   # On Windows (run as Administrator)
   .\generate_ssl_certs.ps1
   ```

8. To stop the containers:
   ```bash
   docker-compose down
   ```

9. To clean up and rebuild:
   ```bash
   # On Windows
   .\docker-run.ps1 -clean -build
   # On Linux/macOS
   docker-compose down -v
   docker system prune -f
   docker-compose build
   ```

## GitHub API Authentication

While the application can work without authentication, it's recommended to use a GitHub personal access token to increase the API rate limit:

1. Create a token at https://github.com/settings/tokens
2. Add the token to your `.env` file as `GITHUB_TOKEN=your_token_here`

## Project Structure

```
github-repo-analyzer/
├── app.py                  # Main Flask application
├── config.py               # Configuration settings
├── models/                 # Database models and API client
│   ├── __init__.py
│   ├── database.py         # SQLAlchemy models
│   └── github_api.py       # GitHub API client
├── static/                 # Static assets
│   ├── css/
│   │   └── style.css       # Custom styles
│   └── js/
│       └── script.js       # Client-side JavaScript
├── templates/              # Jinja2 templates
│   ├── base.html           # Base template
│   ├── index.html          # Home page
│   ├── results.html        # Analysis results
│   ├── history.html        # Previously analyzed repos
│   ├── 404.html            # Not found page
│   └── 500.html            # Server error page
├── .env                    # Environment variables (not in repo)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
└── docker-compose.yml      # Docker Compose configuration
```

## API Endpoints

- `GET /`: Home page with repository input form
- `POST /analyze`: Process repository URL and redirect to results
- `GET /repository/<repo_id>`: View analysis results for a specific repository
- `GET /history`: View previously analyzed repositories
- `GET /api/repository/<repo_id>`: JSON API for repository data

## Technologies Used

- **Backend**: Python, Flask, SQLAlchemy
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5, Chart.js
- **Database**: SQLite
- **API**: GitHub REST API v3
- **Deployment**: Docker, Gunicorn, Nginx

## Docker Architecture

### Optimizations

- **Multi-stage builds**: Reduces final image size by separating build and runtime environments
- **Layer caching**: Optimized Dockerfile structure to leverage Docker's layer caching
- **Volume persistence**: Database and configuration stored in Docker volumes for data persistence
- **Environment variables**: All configuration managed through environment variables for flexibility
- **Health checks**: Container health monitoring to ensure application availability
- **Resource limits**: Configurable worker counts and timeouts for optimal performance

### Container Setup

- **Web container**: Flask application served by Gunicorn with configurable workers
- **Nginx container**: Reverse proxy with SSL termination for production deployments
- **Shared volume**: Persistent storage for SQLite database between container restarts

### Security Features

- **SSL/TLS**: HTTPS support with self-signed certificates (development) or your own certificates (production)
- **Environment isolation**: Sensitive data like API tokens stored in environment variables
- **Read-only file systems**: Nginx configuration mounted as read-only for added security

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [GitHub API Documentation](https://docs.github.com/en/rest)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Bootstrap Documentation](https://getbootstrap.com/docs/5.0/)
- [Chart.js Documentation](https://www.chartjs.org/docs/)
