# PowerShell script to build and run Docker containers for GitHub Repository Analyzer

# Check if .env file exists, if not create it from example
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from .env.example..."
    Copy-Item ".env.example" ".env"
    Write-Host "Please edit the .env file with your settings before continuing."
    Write-Host "Specifically, set your GitHub token to avoid API rate limits."
    exit
}

# Parse command line arguments
param (
    [string]$mode = "dev",
    [switch]$build,
    [switch]$clean
)

# Clean up existing containers if requested
if ($clean) {
    Write-Host "Stopping and removing existing containers..."
    docker-compose down -v
    docker system prune -f
}

# Build images if requested
if ($build) {
    Write-Host "Building Docker images..."
    if ($mode -eq "prod") {
        docker-compose build
    } else {
        docker-compose build web
    }
}

# Run containers based on mode
if ($mode -eq "prod") {
    Write-Host "Starting production containers with Nginx..."
    docker-compose --profile prod up -d
} else {
    Write-Host "Starting development containers..."
    docker-compose up -d
}

# Show container status
docker-compose ps

Write-Host "`nGitHub Repository Analyzer is running!"
if ($mode -eq "prod") {
    Write-Host "Access the application at: http://localhost or https://localhost"
} else {
    Write-Host "Access the application at: http://localhost:5000"
}
Write-Host "To stop the containers, run: docker-compose down"
