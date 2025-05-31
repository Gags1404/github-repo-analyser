import os
import sys
import time
import logging
from datetime import datetime
from flask import Flask
from models.database import init_db, db, Repository, Contributor, Commit
from models.github_api import GitHubAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Sample repositories to test
TEST_REPOS = [
    ("microsoft", "vscode"),
    ("torvalds", "linux"),
    ("facebook", "react"),
    ("octocat", "Hello-World")
]

def create_test_app():
    """Create a test Flask app instance."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///github_repos.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['GITHUB_TOKEN'] = os.environ.get('GITHUB_TOKEN')
    app.config['TESTING'] = True
    
    # Initialize database
    init_db(app)
    
    return app

def test_github_api(github_api):
    """Test the GitHub API client functionality."""
    logger.info("\n=== Testing GitHub API Client ===")
    
    # Test URL parsing
    logger.info("\n--- Testing URL parsing ---")
    test_urls = [
        "https://github.com/microsoft/vscode",
        "github.com/torvalds/linux",
        "http://github.com/facebook/react",
        "microsoft/vscode",
        "https://not-github.com/invalid/url",
        "invalid-url"
    ]
    
    for url in test_urls:
        owner, repo = github_api.parse_repo_url(url)
        logger.info(f"URL: {url} -> Owner: {owner}, Repo: {repo}")
    
    # Test repository data retrieval for a small repo
    owner, repo = "octocat", "Hello-World"
    logger.info(f"\n--- Testing repository data retrieval for {owner}/{repo} ---")
    
    # Get repository data
    repo_data = github_api.get_repository(owner, repo)
    
    if 'error' in repo_data:
        logger.error(f"Error fetching repository: {repo_data['error']}")
        return False
    else:
        logger.info(f"Repository data fetched successfully")
        logger.info(f"Name: {repo_data.get('name')}")
        logger.info(f"Stars: {repo_data.get('stargazers_count')}")
        logger.info(f"Forks: {repo_data.get('forks_count')}")
        
        # Get additional data
        contributors = github_api.get_contributors(owner, repo)
        commits = github_api.get_commits(owner, repo)
        commit_activity = github_api.get_commit_activity(owner, repo)
        languages = github_api.get_languages(owner, repo)
        
        if isinstance(contributors, list):
            logger.info(f"Contributors: {len(contributors)}")
        if isinstance(commits, list):
            logger.info(f"Commits: {len(commits)}")
        if isinstance(commit_activity, list):
            logger.info(f"Commit activity weeks: {len(commit_activity)}")
        if isinstance(languages, dict) and not 'error' in languages:
            logger.info(f"Languages: {', '.join(languages.keys())}")
        
        return True

def test_database_operations(app, github_api):
    """Test database operations."""
    logger.info("\n=== Testing Database Operations ===")
    
    owner, repo = "octocat", "Hello-World"  # Small repository for quick testing
    
    with app.app_context():
        try:
            # Step 1: Clean up any existing data for this repository
            logger.info(f"Cleaning up existing data for {owner}/{repo}")
            existing_repo = Repository.query.filter_by(owner=owner, name=repo).first()
            if existing_repo:
                logger.info(f"Deleting existing repository: {existing_repo.full_name}")
                db.session.delete(existing_repo)
                db.session.commit()
            
            # Step 2: Fetch repository data from GitHub API
            logger.info(f"Fetching data for {owner}/{repo} from GitHub API")
            repo_data = github_api.get_repository(owner, repo)
            
            if 'error' in repo_data:
                logger.error(f"Error fetching repository: {repo_data['error']}")
                return False
            
            # Step 3: Create repository in database
            logger.info("Creating repository in database")
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
            
            # Step 4: Fetch and add contributors
            logger.info("Fetching and adding contributors")
            contributors_data = github_api.get_contributors(owner, repo)
            
            if not isinstance(contributors_data, list):
                logger.warning(f"Error fetching contributors: {contributors_data.get('error')}")
                contributors_data = []
            
            for contributor in contributors_data:
                new_contributor = Contributor(
                    repository_id=repo_id,
                    username=contributor.get('login'),
                    avatar_url=contributor.get('avatar_url'),
                    html_url=contributor.get('html_url'),
                    contributions=contributor.get('contributions', 0)
                )
                db.session.add(new_contributor)
            
            # Step 5: Fetch and add commits
            logger.info("Fetching and adding commits")
            commits_data = github_api.get_commits(owner, repo)
            
            if not isinstance(commits_data, list):
                logger.warning(f"Error fetching commits: {commits_data.get('error')}")
                commits_data = []
            
            for commit in commits_data[:10]:  # Limit to 10 commits for testing
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
            
            # Commit all changes
            db.session.commit()
            logger.info("Successfully saved repository data to database")
            
            # Step 6: Verify data was saved correctly
            logger.info("\nVerifying database data:")
            
            # Check repository
            saved_repo = Repository.query.filter_by(owner=owner, name=repo).first()
            if not saved_repo:
                logger.error("Repository not found in database!")
                return False
            
            logger.info(f"Repository: {saved_repo.full_name}")
            logger.info(f"Stars: {saved_repo.stars}")
            logger.info(f"Forks: {saved_repo.forks}")
            
            # Check contributors
            contributors = Contributor.query.filter_by(repository_id=saved_repo.id).all()
            logger.info(f"Contributors: {len(contributors)}")
            
            # Check commits
            commits = Commit.query.filter_by(repository_id=saved_repo.id).all()
            logger.info(f"Commits: {len(commits)}")
            
            logger.info("\nDatabase test completed successfully!")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during database test: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def test_error_handling(github_api):
    """Test error handling for invalid repositories."""
    logger.info("\n=== Testing Error Handling ===")
    
    # Test non-existent repository
    owner, repo = "nonexistent-user", "nonexistent-repo"
    logger.info(f"Testing non-existent repository: {owner}/{repo}")
    
    repo_data = github_api.get_repository(owner, repo)
    
    if 'error' in repo_data and repo_data['error'] == 'not_found':
        logger.info("Successfully detected non-existent repository")
        return True
    else:
        logger.error(f"Failed to detect non-existent repository: {repo_data}")
        return False

def run_all_tests():
    """Run all tests for the GitHub Repository Analyzer."""
    logger.info("Starting GitHub Repository Analyzer tests")
    
    # Create test app
    app = create_test_app()
    
    # Initialize GitHub API client
    token = os.environ.get('GITHUB_TOKEN')
    github_api = GitHubAPI(token=token)
    
    logger.info(f"Using GitHub API token: {'Yes' if token else 'No'}")
    
    # Run tests
    api_test_result = test_github_api(github_api)
    db_test_result = test_database_operations(app, github_api)
    error_test_result = test_error_handling(github_api)
    
    # Print summary
    logger.info("\n=== Test Results Summary ===")
    logger.info(f"GitHub API Test: {'PASSED' if api_test_result else 'FAILED'}")
    logger.info(f"Database Operations Test: {'PASSED' if db_test_result else 'FAILED'}")
    logger.info(f"Error Handling Test: {'PASSED' if error_test_result else 'FAILED'}")
    
    all_passed = api_test_result and db_test_result and error_test_result
    logger.info(f"\nOverall Result: {'PASSED' if all_passed else 'FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    # Set GitHub token from environment if available
    if 'GITHUB_TOKEN' not in os.environ and len(sys.argv) > 1:
        os.environ['GITHUB_TOKEN'] = sys.argv[1]
        
    run_all_tests()
