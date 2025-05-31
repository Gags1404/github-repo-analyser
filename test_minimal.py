import os
import sys
import logging
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

def test_url_parsing():
    """Test the URL parsing functionality."""
    logger.info("\n=== Testing URL Parsing ===")
    
    # Initialize GitHub API client
    github_api = GitHubAPI()
    
    test_cases = [
        # Valid URLs
        ("https://github.com/microsoft/vscode", "microsoft", "vscode"),
        ("http://github.com/facebook/react", "facebook", "react"),
        ("microsoft/vscode", "microsoft", "vscode"),
        # Invalid URLs
        ("github.com/torvalds/linux", "torvalds", "linux"),  # This should now work
        ("https://not-github.com/invalid/url", None, None),  # Wrong domain
        ("invalid-url", None, None),  # Not a URL
        ("", None, None),  # Empty string
    ]
    
    passed = 0
    failed = 0
    
    for url, expected_owner, expected_repo in test_cases:
        owner, repo = github_api.parse_repo_url(url)
        
        if owner == expected_owner and repo == expected_repo:
            logger.info(f"✓ PASS: URL '{url}' -> Owner: '{owner}', Repo: '{repo}'")
            passed += 1
        else:
            logger.error(f"✗ FAIL: URL '{url}' -> Got: Owner: '{owner}', Repo: '{repo}', Expected: Owner: '{expected_owner}', Repo: '{expected_repo}'")
            failed += 1
    
    logger.info(f"\nURL Parsing Test Results: {passed} passed, {failed} failed")
    return passed > 0 and failed == 0

def test_minimal_api():
    """Test minimal API functionality to avoid rate limits."""
    logger.info("\n=== Testing Minimal API Functionality ===")
    
    # Initialize GitHub API client with token
    token = "test_github_token"
    github_api = GitHubAPI(token=token)
    
    # Test a small repository
    owner, repo = "octocat", "Hello-World"
    logger.info(f"Testing repository: {owner}/{repo}")
    
    # Get repository data
    repo_data = github_api.get_repository(owner, repo)
    
    if 'error' in repo_data:
        logger.error(f"Error fetching repository: {repo_data['error']}")
        if repo_data['error'] == 'rate_limit_exceeded':
            logger.warning("Rate limit exceeded. Skipping further API tests.")
            return False
        return False
    
    # Basic verification
    if repo_data.get('name') == repo and repo_data.get('owner', {}).get('login') == owner:
        logger.info(f"✓ PASS: Repository data fetched successfully")
        logger.info(f"  Name: {repo_data.get('name')}")
        logger.info(f"  Stars: {repo_data.get('stargazers_count')}")
        logger.info(f"  Forks: {repo_data.get('forks_count')}")
        return True
    else:
        logger.error(f"✗ FAIL: Repository data does not match expected values")
        return False

def test_error_handling():
    """Test error handling for invalid repositories."""
    logger.info("\n=== Testing Error Handling ===")
    
    # Initialize GitHub API client with token
    token = "test_github_token"
    github_api = GitHubAPI(token=token)
    
    # Test non-existent repository
    owner, repo = "nonexistent-user", "nonexistent-repo"
    logger.info(f"Testing non-existent repository: {owner}/{repo}")
    
    repo_data = github_api.get_repository(owner, repo)
    
    if 'error' in repo_data:
        if repo_data['error'] == 'rate_limit_exceeded':
            logger.warning("Rate limit exceeded. Skipping error handling test.")
            return True  # Skip this test if rate limited
        
        if repo_data['error'] == 'not_found':
            logger.info(f"✓ PASS: Successfully detected non-existent repository")
            return True
        else:
            logger.error(f"✗ FAIL: Wrong error type for non-existent repository: {repo_data['error']}")
            return False
    else:
        logger.error(f"✗ FAIL: Failed to detect non-existent repository")
        return False

def run_minimal_tests():
    """Run minimal tests that don't hit rate limits as much."""
    logger.info("Starting minimal GitHub Repository Analyzer tests")
    
    # Run tests
    url_parsing_result = test_url_parsing()
    api_test_result = test_minimal_api()
    error_handling_result = test_error_handling()
    
    # Print summary
    logger.info("\n=== Test Results Summary ===")
    logger.info(f"URL Parsing Test: {'PASSED' if url_parsing_result else 'FAILED'}")
    logger.info(f"Minimal API Test: {'PASSED' if api_test_result else 'FAILED'}")
    logger.info(f"Error Handling Test: {'PASSED' if error_handling_result else 'FAILED'}")
    
    all_passed = url_parsing_result and api_test_result and error_handling_result
    logger.info(f"\nOverall Result: {'PASSED' if all_passed else 'FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    # Set GitHub token from environment if available
    if 'GITHUB_TOKEN' not in os.environ and len(sys.argv) > 1:
        os.environ['GITHUB_TOKEN'] = sys.argv[1]
        
    run_minimal_tests()
