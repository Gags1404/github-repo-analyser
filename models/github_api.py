import requests
import time
from datetime import datetime
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GitHubAPI:
    """GitHub API client for fetching repository data."""
    
    def __init__(self, token=None, api_url='https://api.github.com'):
        """Initialize the GitHub API client.
        
        Args:
            token (str, optional): GitHub personal access token
            api_url (str, optional): GitHub API base URL
        """
        self.api_url = api_url
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
        }
        
        # Add token to headers if provided
        if token:
            self.headers['Authorization'] = f'token {token}'
        
        # Track rate limit
        self.rate_limit = None
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
    
    def _update_rate_limit(self, response):
        """Update rate limit information from API response headers."""
        if 'X-RateLimit-Limit' in response.headers:
            self.rate_limit = int(response.headers['X-RateLimit-Limit'])
            self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
            self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
            
            # Log rate limit info
            logger.debug(f"Rate limit: {self.rate_limit_remaining}/{self.rate_limit}, "
                         f"resets at {datetime.fromtimestamp(self.rate_limit_reset)}")
    
    def _make_request(self, url, method='GET', params=None, max_retries=3, retry_delay=2, max_wait=60):
        """Make a request to the GitHub API with retry logic and rate limit handling.
        
        Args:
            url (str): API endpoint URL
            method (str): HTTP method (default: 'GET')
            params (dict): Query parameters
            max_retries (int): Maximum number of retries
            retry_delay (int): Delay between retries in seconds
            max_wait (int): Maximum time to wait for rate limit reset in seconds
            
        Returns:
            dict or list: API response or error dict
        """
        
        retries = 0
        while retries <= max_retries:
            try:
                response = requests.request(
                    method,
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=10
                )
                
                # Update rate limit info
                self._update_rate_limit(response)
                
                # Check for rate limit
                remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                
                if remaining < 5 and reset_time > 0:
                    wait_time = reset_time - int(time.time())
                    if wait_time > 0 and wait_time <= max_wait:
                        logger.warning(f"Rate limit almost exhausted. Waiting for {wait_time} seconds.")
                        time.sleep(wait_time + 1)  # Add 1 second buffer
                    elif wait_time > max_wait:
                        logger.warning(f"Rate limit almost exhausted but wait time ({wait_time}s) exceeds max wait. Proceeding with caution.")
                
                # Handle rate limit exceeded
                if response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
                    reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                    wait_time = reset_time - int(time.time())
                    
                    if wait_time > 0 and wait_time <= max_wait:  # Only wait if less than max_wait
                        logger.warning(f"Rate limit exceeded. Waiting for {wait_time} seconds.")
                        time.sleep(wait_time + 1)  # Add 1 second buffer
                        retries += 1
                        continue
                    else:
                        logger.error(f"Rate limit exceeded. Reset time too long ({wait_time}s).")
                        return {
                            'error': 'rate_limit_exceeded', 
                            'message': 'GitHub API rate limit exceeded. Try again later or add a GitHub token.'
                        }
                
                # Handle other HTTP errors
                if response.status_code == 404:
                    logger.error(f"Resource not found: {url}")
                    return {'error': 'not_found', 'message': 'Repository not found'}
                elif response.status_code == 403 and 'forbidden' in response.text.lower():
                    logger.error(f"Access forbidden: {url}")
                    return {'error': 'forbidden', 'message': 'Access to this repository is forbidden'}
                elif response.status_code >= 400:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    return {'error': 'api_error', 'message': f'GitHub API error: {response.status_code}'}
                
                # Return JSON response
                return response.json()
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout: {url}. Retrying...")
                retries += 1
                time.sleep(min(retry_delay * (2 ** retries), 30))  # Exponential backoff with cap
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                return {'error': 'request_error', 'message': str(e)}
                
            except ValueError as e:  # JSON parsing error
                logger.error(f"JSON parsing error: {e}")
                return {'error': 'json_error', 'message': 'Invalid response format'}
            
            retries += 1  # Increment retry counter if we get here
        
        return {'error': 'max_retries_exceeded', 'details': f'Failed after {max_retries} retries'}
    
    def parse_repo_url(self, url):
        """Parse a GitHub repository URL to extract owner and repo name.
        
        Args:
            url (str): GitHub repository URL or owner/repo string
            
        Returns:
            tuple: (owner, repo) or (None, None) if invalid
        """
        if not url:
            return None, None
        
        # Handle direct owner/repo format (e.g. microsoft/vscode)
        if '/' in url and not url.startswith('http') and not url.startswith('www') and not url.startswith('github'):
            parts = url.strip().split('/')
            if len(parts) == 2 and all(parts):
                return parts[0], parts[1]
        
        # Handle URL format
        try:
            # If URL doesn't start with http(s)://, add it
            if not url.startswith('http'):
                url = 'https://' + url
                    
            parsed_url = urlparse(url)
            
            # Check if it's a GitHub URL - must be exactly github.com domain
            if not parsed_url.netloc or parsed_url.netloc not in ('github.com', 'www.github.com'):
                return None, None
                
            # Extract path parts
            path_parts = [p for p in parsed_url.path.strip('/').split('/') if p]
            
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1]
        except Exception as e:
            logger.error(f"Error parsing URL: {e}")
        
        return None, None
    
    def get_repository(self, owner, repo):
        """Get repository information.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            
        Returns:
            dict: Repository data or error information
        """
        url = f"{self.api_url}/repos/{owner}/{repo}"
        return self._make_request(url)
    
    def get_contributors(self, owner, repo, limit=10):
        """Get repository contributors.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            limit (int, optional): Maximum number of contributors to return
            
        Returns:
            list: Contributors data or error information
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/contributors"
        params = {'per_page': limit}
        return self._make_request(url, params=params)
    
    def get_commits(self, owner, repo, limit=20):
        """Get repository commits.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            limit (int, optional): Maximum number of commits to return
            
        Returns:
            list: Commits data or error information
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/commits"
        params = {'per_page': limit}
        return self._make_request(url, params=params)
    
    def get_commit_activity(self, owner, repo):
        """Get commit activity for the past year.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            
        Returns:
            list: Weekly commit counts for the past year
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/stats/commit_activity"
        return self._make_request(url)
    
    def get_languages(self, owner, repo):
        """Get language breakdown for a repository.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            
        Returns:
            dict: Language data with byte counts
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/languages"
        return self._make_request(url)
