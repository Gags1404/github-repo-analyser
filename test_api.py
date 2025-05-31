import os
import sys
import time
import logging
from datetime import datetime
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

# Invalid repositories to test error handling
INVALID_REPOS = [
    ("nonexistent-user", "nonexistent-repo"),
    ("github", "private-repo-that-doesnt-exist")
]

def test_github_api():
    """Test the GitHub API client functionality."""
    # Initialize GitHub API client
    token = os.environ.get('GITHUB_TOKEN')
    github_api = GitHubAPI(token=token)
    
    logger.info(f"Testing GitHub API client with token: {'Yes' if token else 'No'}")
    
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
    
    # Test repository data retrieval
    logger.info("\n--- Testing repository data retrieval ---")
    for owner, repo in TEST_REPOS:
        logger.info(f"\nTesting repository: {owner}/{repo}")
        
        # Get repository data
        start_time = time.time()
        repo_data = github_api.get_repository(owner, repo)
        elapsed = time.time() - start_time
        
        if 'error' in repo_data:
            logger.error(f"Error fetching repository: {repo_data['error']}")
            if repo_data['error'] == 'rate_limit_exceeded':
                wait_time = repo_data.get('wait_time', 0)
                logger.warning(f"Rate limit exceeded. Reset in {wait_time:.1f} seconds.")
                if wait_time < 300:  # Only wait if less than 5 minutes
                    logger.info(f"Waiting for rate limit reset...")
                    time.sleep(wait_time + 1)
                    # Try again after waiting
                    repo_data = github_api.get_repository(owner, repo)
        else:
            logger.info(f"Repository data fetched successfully in {elapsed:.2f} seconds")
            logger.info(f"Name: {repo_data.get('name')}")
            logger.info(f"Stars: {repo_data.get('stargazers_count')}")
            logger.info(f"Forks: {repo_data.get('forks_count')}")
            logger.info(f"Open Issues: {repo_data.get('open_issues_count')}")
            logger.info(f"Language: {repo_data.get('language')}")
            
            # Get additional data
            logger.info("\nFetching additional data...")
            
            # Contributors
            contributors = github_api.get_contributors(owner, repo)
            if isinstance(contributors, list):
                logger.info(f"Contributors: {len(contributors)}")
            else:
                logger.error(f"Error fetching contributors: {contributors.get('error')}")
            
            # Commits
            commits = github_api.get_commits(owner, repo)
            if isinstance(commits, list):
                logger.info(f"Commits: {len(commits)}")
            else:
                logger.error(f"Error fetching commits: {commits.get('error')}")
            
            # Commit activity
            commit_activity = github_api.get_commit_activity(owner, repo)
            if isinstance(commit_activity, list):
                logger.info(f"Commit activity weeks: {len(commit_activity)}")
            else:
                logger.error(f"Error fetching commit activity: {commit_activity.get('error')}")
            
            # Languages
            languages = github_api.get_languages(owner, repo)
            if isinstance(languages, dict) and not 'error' in languages:
                logger.info(f"Languages: {', '.join(languages.keys())}")
            else:
                logger.error(f"Error fetching languages: {languages.get('error')}")
        
        # Add a small delay between requests to avoid hitting rate limits
        time.sleep(2)
    
    # Test error handling with invalid repositories
    logger.info("\n--- Testing error handling with invalid repositories ---")
    for owner, repo in INVALID_REPOS:
        logger.info(f"\nTesting invalid repository: {owner}/{repo}")
        repo_data = github_api.get_repository(owner, repo)
        
        if 'error' in repo_data:
            logger.info(f"Successfully detected error: {repo_data['error']}")
            logger.info(f"Error details: {repo_data.get('message', repo_data.get('details', 'No details'))}")
        else:
            logger.error(f"Failed to detect invalid repository: {owner}/{repo}")
        
        # Add a small delay between requests
        time.sleep(1)

if __name__ == "__main__":
    # Set GitHub token from environment if available
    if 'GITHUB_TOKEN' not in os.environ and len(sys.argv) > 1:
        os.environ['GITHUB_TOKEN'] = sys.argv[1]
        
    test_github_api()
