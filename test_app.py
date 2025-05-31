import os
import sys
import time
import logging
from datetime import datetime
from flask import Flask
from models.database import init_db, db, Repository, Contributor, Commit
from models.github_api import GitHubAPI

# Import environment variables from test_env.py
import test_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Environment variables are loaded from test_env.py

def create_test_app():
    """Create a test Flask app instance."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///test_github_analyzer.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['GITHUB_TOKEN'] = os.getenv('GITHUB_TOKEN')
    app.config['CACHE_TIMEOUT'] = int(os.getenv('CACHE_TIMEOUT', 3600))
    app.config['TESTING'] = True
    
    # Initialize database
    init_db(app)
    
    return app

def test_repository(github_api, owner, repo, app):
    """Test analyzing a repository."""
    logger.info(f"Testing repository: {owner}/{repo}")
    
    # Check if repository exists in database and is not stale
    with app.app_context():
        existing_repo = Repository.query.filter_by(owner=owner, name=repo).first()
        
        if existing_repo and (datetime.utcnow() - existing_repo.last_analyzed).total_seconds() < app.config.get('CACHE_TIMEOUT'):
            logger.info(f"Using cached data for {owner}/{repo}")
            return True, existing_repo.id
    
    # Fetch repository data from GitHub API
    repo_data = github_api.get_repository(owner, repo)
    
    # Check for errors
    if 'error' in repo_data:
        error_type = repo_data['error']
        logger.error(f"Error fetching repository {owner}/{repo}: {error_type}")
        if error_type == 'rate_limit_exceeded':
            wait_time = repo_data.get('wait_time', 0)
            logger.warning(f"Rate limit exceeded. Reset in {wait_time:.1f} seconds.")
            if wait_time < 300:  # Only wait if less than 5 minutes
                logger.info(f"Waiting for rate limit reset...")
                time.sleep(wait_time + 1)
                # Try again after waiting
                return test_repository(github_api, owner, repo, app)
        return False, None
    
    # Get additional data
    contributors_data = github_api.get_contributors(owner, repo)
    commits_data = github_api.get_commits(owner, repo)
    commit_activity = github_api.get_commit_activity(owner, repo)
    languages_data = github_api.get_languages(owner, repo)
    
    # Check for errors in additional data
    if isinstance(contributors_data, dict) and 'error' in contributors_data:
        logger.warning(f"Error fetching contributors for {owner}/{repo}: {contributors_data.get('details', 'Unknown error')}")
        contributors_data = []
    
    if isinstance(commits_data, dict) and 'error' in commits_data:
        logger.warning(f"Error fetching commits for {owner}/{repo}: {commits_data.get('details', 'Unknown error')}")
        commits_data = []
    
    if isinstance(commit_activity, dict) and 'error' in commit_activity:
        logger.warning(f"Error fetching commit activity for {owner}/{repo}: {commit_activity.get('details', 'Unknown error')}")
        commit_activity = []
    
    if isinstance(languages_data, dict) and 'error' in languages_data:
        logger.warning(f"Error fetching languages for {owner}/{repo}: {languages_data.get('details', 'Unknown error')}")
        languages_data = {}
    
    # Save repository to database
    with app.app_context():
        try:
            # Check if repository already exists
            existing_repo = Repository.query.filter_by(owner=owner, name=repo).first()
            
            if existing_repo:
                # Update existing repository
                existing_repo.stars = repo_data.get('stargazers_count', 0)
                existing_repo.forks = repo_data.get('forks_count', 0)
                existing_repo.watchers = repo_data.get('watchers_count', 0)
                existing_repo.open_issues = repo_data.get('open_issues_count', 0)
                existing_repo.primary_language = repo_data.get('language')
                existing_repo.updated_at = datetime.strptime(repo_data.get('updated_at'), '%Y-%m-%dT%H:%M:%SZ') if repo_data.get('updated_at') else None
                existing_repo.last_analyzed = datetime.utcnow()
                
                # Clear existing contributors and commits
                Contributor.query.filter_by(repository_id=existing_repo.id).delete()
                Commit.query.filter_by(repository_id=existing_repo.id).delete()
                
                repo_id = existing_repo.id
            else:
                # Create new repository
                new_repo = Repository(
                    name=repo,
                    owner=owner,
                    full_name=f"{owner}/{repo}",
                    description=repo_data.get('description'),
                    html_url=repo_data.get('html_url'),
                    api_url=repo_data.get('url'),
                    stars=repo_data.get('stargazers_count', 0),
                    forks=repo_data.get('forks_count', 0),
                    watchers=repo_data.get('watchers_count', 0),
                    open_issues=repo_data.get('open_issues_count', 0),
                    primary_language=repo_data.get('language'),
                    created_at=datetime.strptime(repo_data.get('created_at'), '%Y-%m-%dT%H:%M:%SZ') if repo_data.get('created_at') else None,
                    updated_at=datetime.strptime(repo_data.get('updated_at'), '%Y-%m-%dT%H:%M:%SZ') if repo_data.get('updated_at') else None,
                    size=repo_data.get('size', 0),
                    default_branch=repo_data.get('default_branch', 'main'),
                    last_analyzed=datetime.utcnow()
                )
                db.session.add(new_repo)
                db.session.flush()  # Get ID before committing
                repo_id = new_repo.id
            
            # Add contributors
            for contributor in contributors_data:
                new_contributor = Contributor(
                    repository_id=repo_id,
                    username=contributor.get('login'),
                    avatar_url=contributor.get('avatar_url'),
                    html_url=contributor.get('html_url'),
                    contributions=contributor.get('contributions', 0)
                )
                db.session.add(new_contributor)
            
            # Add commits (limited to 100 most recent)
            for commit in commits_data[:100]:
                commit_data = commit.get('commit', {})
                author_data = commit_data.get('author', {})
                committer_data = commit_data.get('committer', {})
                
                new_commit = Commit(
                    repository_id=repo_id,
                    sha=commit.get('sha'),
                    message=commit_data.get('message'),
                    author_name=author_data.get('name'),
                    author_email=author_data.get('email'),
                    author_date=datetime.strptime(author_data.get('date'), '%Y-%m-%dT%H:%M:%SZ') if author_data.get('date') else None,
                    committer_name=committer_data.get('name'),
                    committer_email=committer_data.get('email'),
                    committer_date=datetime.strptime(committer_data.get('date'), '%Y-%m-%dT%H:%M:%SZ') if committer_data.get('date') else None,
                    html_url=commit.get('html_url')
                )
                db.session.add(new_commit)
            
            db.session.commit()
            logger.info(f"Successfully saved repository {owner}/{repo} to database")
            return True, repo_id
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving repository {owner}/{repo} to database: {str(e)}")
            return False, None

def test_invalid_repository(github_api):
    """Test analyzing an invalid repository."""
    logger.info("Testing invalid repository")
    
    # Test non-existent repository
    owner, repo = "nonexistent-user", "nonexistent-repo"
    repo_data = github_api.get_repository(owner, repo)
    
    if 'error' in repo_data and repo_data['error'] == 'not_found':
        logger.info("Successfully detected non-existent repository")
    else:
        logger.error(f"Failed to detect non-existent repository: {repo_data}")
    
    # Test invalid URL
    result = github_api.parse_repo_url("https://not-github.com/invalid/url")
    if result == (None, None):
        logger.info("Successfully detected invalid URL")
    else:
        logger.error(f"Failed to detect invalid URL: {result}")

def main():
    """Main test function."""
    logger.info("Starting GitHub Repository Analyzer tests")
    
    # Create test app
    app = create_test_app()
    
    # Initialize GitHub API client
    github_api = GitHubAPI(token=app.config.get('GITHUB_TOKEN'))
    
    # Test sample repositories
    test_repos = [
        ("microsoft", "vscode"),
        ("torvalds", "linux"),
        ("facebook", "react"),
        ("octocat", "Hello-World")
    ]
    
    results = []
    for owner, repo in test_repos:
        success, repo_id = test_repository(github_api, owner, repo, app)
        results.append((owner, repo, success, repo_id))
        # Add a small delay between requests to avoid hitting rate limits
        time.sleep(2)
    
    # Test invalid repositories
    test_invalid_repository(github_api)
    
    # Print results
    logger.info("\n----- Test Results -----")
    for owner, repo, success, repo_id in results:
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"{owner}/{repo}: {status} (ID: {repo_id})")
    
    # Verify database storage and retrieval
    with app.app_context():
        repo_count = Repository.query.count()
        contributor_count = Contributor.query.count()
        commit_count = Commit.query.count()
        
        logger.info(f"\nDatabase Statistics:")
        logger.info(f"Repositories: {repo_count}")
        logger.info(f"Contributors: {contributor_count}")
        logger.info(f"Commits: {commit_count}")
        
        # Verify we can retrieve data for each repository
        for owner, repo, success, repo_id in results:
            if success and repo_id:
                repo_obj = Repository.query.get(repo_id)
                if repo_obj:
                    contributors = Contributor.query.filter_by(repository_id=repo_id).count()
                    commits = Commit.query.filter_by(repository_id=repo_id).count()
                    logger.info(f"{owner}/{repo} - Contributors: {contributors}, Commits: {commits}")
                else:
                    logger.error(f"Could not retrieve {owner}/{repo} from database")

if __name__ == "__main__":
    main()
