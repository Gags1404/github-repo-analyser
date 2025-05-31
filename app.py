import os
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from models.database import init_db, db, Repository, Contributor, Commit
from models.github_api import GitHubAPI
from config import get_config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(get_config())

# Set secret key for session
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-for-testing')

# Register custom Jinja2 filters
@app.template_filter('format_number')
def format_number(value):
    """Format numbers for display (e.g., 1000 -> 1k)"""
    if value is None:
        return '0'
    
    value = int(value)
    if value < 1000:
        return str(value)
    elif value < 1000000:
        return f"{value/1000:.1f}k".replace('.0k', 'k')
    else:
        return f"{value/1000000:.1f}M".replace('.0M', 'M')

# Initialize database
init_db(app)

# Initialize GitHub API client
github_api = GitHubAPI(token=app.config.get('GITHUB_TOKEN'))

@app.route('/')
def index():
    """Home page with repository input form."""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_repository():
    """Analyze a GitHub repository."""
    repo_url = request.form.get('repo_url', '')
    
    # Parse the repository URL
    owner, repo = github_api.parse_repo_url(repo_url)
    
    if not owner or not repo:
        flash('Invalid GitHub repository URL. Please enter a valid URL in the format "owner/repo" or "https://github.com/owner/repo".', 'danger')
        return redirect(url_for('index'))
    
    # Check if repository exists in database
    existing_repo = Repository.query.filter_by(owner=owner, name=repo).first()
    
    # If repository exists and was analyzed recently, use cached data
    if existing_repo and (datetime.utcnow() - existing_repo.last_analyzed).days < 1:
        flash(f'Using cached data for {owner}/{repo} (analyzed {existing_repo.last_analyzed}).', 'info')
        return redirect(url_for('view_repository', repo_id=existing_repo.id))
    
    # Fetch repository data from GitHub API
    repo_data = github_api.get_repository(owner, repo)
    
    # Handle API errors
    if 'error' in repo_data:
        error_type = repo_data['error']
        if error_type == 'rate_limit_exceeded':
            wait_time = repo_data.get('wait_time', 0)
            reset_time = datetime.fromtimestamp(time.time() + wait_time)
            flash(f'GitHub API rate limit exceeded. Rate limit will reset at {reset_time.strftime("%H:%M:%S")}. Please try again later.', 'warning')
        elif error_type == 'not_found':
            flash(f'Repository {owner}/{repo} not found. It may be private or doesn\'t exist.', 'danger')
        elif error_type == 'forbidden':
            flash('Access to this repository is forbidden. It may be private or you may need authentication.', 'danger')
            if not app.config.get('GITHUB_TOKEN'):
                flash('Consider adding a GitHub personal access token to increase your rate limit.', 'info')
        elif error_type == 'timeout':
            flash('Request to GitHub API timed out. GitHub might be experiencing high load or the repository might be very large.', 'warning')
        elif error_type == 'server_error':
            flash('GitHub API server error. Please try again later.', 'error')
        else:
            flash(f'Error fetching repository data: {repo_data.get("details", "Unknown error")}', 'error')
        return redirect(url_for('index'))
    
    # Get contributors and commits
    contributors_data = github_api.get_contributors(owner, repo)
    commits_data = github_api.get_commits(owner, repo)
    commit_activity = github_api.get_commit_activity(owner, repo)
    languages_data = github_api.get_languages(owner, repo)
    
    # Check for errors in additional data and provide appropriate defaults
    if isinstance(contributors_data, dict) and 'error' in contributors_data:
        app.logger.warning(f"Error fetching contributors: {contributors_data.get('details', 'Unknown error')}")
        contributors_data = []
        flash('Could not fetch contributor data. Some information may be incomplete.', 'warning')
        
    if isinstance(commits_data, dict) and 'error' in commits_data:
        app.logger.warning(f"Error fetching commits: {commits_data.get('details', 'Unknown error')}")
        commits_data = []
        flash('Could not fetch commit data. Some information may be incomplete.', 'warning')
        
    if isinstance(commit_activity, dict) and 'error' in commit_activity:
        app.logger.warning(f"Error fetching commit activity: {commit_activity.get('details', 'Unknown error')}")
        commit_activity = []
        # Don't flash another message to avoid overwhelming the user
        
    if isinstance(languages_data, dict) and 'error' in languages_data:
        app.logger.warning(f"Error fetching languages: {languages_data.get('details', 'Unknown error')}")
        languages_data = {}
        # Don't flash another message to avoid overwhelming the user
    
    # Save or update repository in database
    if existing_repo:
        # Update existing repository
        existing_repo.description = repo_data.get('description', '')
        existing_repo.stars = repo_data.get('stargazers_count', 0)
        existing_repo.forks = repo_data.get('forks_count', 0)
        existing_repo.watchers = repo_data.get('watchers_count', 0)
        existing_repo.open_issues = repo_data.get('open_issues_count', 0)
        existing_repo.primary_language = repo_data.get('language', '')
        existing_repo.created_at = datetime.fromisoformat(repo_data.get('created_at', '').replace('Z', '+00:00'))
        existing_repo.updated_at = datetime.fromisoformat(repo_data.get('updated_at', '').replace('Z', '+00:00'))
        existing_repo.size = repo_data.get('size', 0)
        existing_repo.default_branch = repo_data.get('default_branch', 'main')
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
            description=repo_data.get('description', ''),
            html_url=repo_data.get('html_url', ''),
            api_url=repo_data.get('url', ''),
            stars=repo_data.get('stargazers_count', 0),
            forks=repo_data.get('forks_count', 0),
            watchers=repo_data.get('watchers_count', 0),
            open_issues=repo_data.get('open_issues_count', 0),
            primary_language=repo_data.get('language', ''),
            created_at=datetime.fromisoformat(repo_data.get('created_at', '').replace('Z', '+00:00')) if repo_data.get('created_at') else None,
            updated_at=datetime.fromisoformat(repo_data.get('updated_at', '').replace('Z', '+00:00')) if repo_data.get('updated_at') else None,
            size=repo_data.get('size', 0),
            default_branch=repo_data.get('default_branch', 'main'),
            last_analyzed=datetime.utcnow()
        )
        db.session.add(new_repo)
        db.session.flush()  # Get ID without committing
        repo_id = new_repo.id
    
    # Save contributors
    for contributor in contributors_data:
        new_contributor = Contributor(
            repository_id=repo_id,
            username=contributor.get('login', ''),
            avatar_url=contributor.get('avatar_url', ''),
            html_url=contributor.get('html_url', ''),
            contributions=contributor.get('contributions', 0)
        )
        db.session.add(new_contributor)
    
    # Save commits
    for commit in commits_data:
        commit_data = commit.get('commit', {})
        author_data = commit_data.get('author', {})
        committer_data = commit_data.get('committer', {})
        
        new_commit = Commit(
            repository_id=repo_id,
            sha=commit.get('sha', ''),
            message=commit_data.get('message', ''),
            author_name=author_data.get('name', ''),
            author_email=author_data.get('email', ''),
            author_date=datetime.fromisoformat(author_data.get('date', '').replace('Z', '+00:00')) if author_data.get('date') else None,
            committer_name=committer_data.get('name', ''),
            committer_email=committer_data.get('email', ''),
            committer_date=datetime.fromisoformat(committer_data.get('date', '').replace('Z', '+00:00')) if committer_data.get('date') else None,
            html_url=commit.get('html_url', '')
        )
        db.session.add(new_commit)
    
    # Commit changes to database
    db.session.commit()
    
    # Store commit activity and languages in session for visualization
    if commit_activity:
        session['commit_activity'] = commit_activity
    if languages_data:
        session['languages_data'] = languages_data
    
    return redirect(url_for('view_repository', repo_id=repo_id))

@app.route('/repository/<int:repo_id>')
def view_repository(repo_id):
    """View repository analysis results."""
    repository = Repository.query.get_or_404(repo_id)
    contributors = Contributor.query.filter_by(repository_id=repo_id).order_by(Contributor.contributions.desc()).all()
    commits = Commit.query.filter_by(repository_id=repo_id).order_by(Commit.author_date.desc()).all()
    
    # Get commit activity data for visualization
    # Instead of relying on session data which may be lost, we'll generate mock data if none exists
    commit_activity = session.get('commit_activity', [])
    languages_data = session.get('languages_data', {})
    
    # If no commit activity data is available, create some sample data based on commits
    if not commit_activity:
        # Create weekly buckets for the last 12 weeks
        now = datetime.utcnow()
        commit_activity = []
        for i in range(12):
            # Calculate week timestamp (seconds since epoch)
            week_timestamp = int((now.timestamp() - (i * 7 * 24 * 60 * 60)))
            # Count commits in this week
            week_commits = sum(1 for c in commits if c.author_date and 
                              abs((c.author_date.timestamp() - week_timestamp) / (7 * 24 * 60 * 60)) < 1)
            commit_activity.append({
                'week': week_timestamp,
                'total': week_commits
            })
        # Reverse to get chronological order
        commit_activity.reverse()
    
    # Define language colors for visualization
    language_colors = {
        'JavaScript': '#f1e05a',
        'Python': '#3572A5',
        'Java': '#b07219',
        'C++': '#f34b7d',
        'C#': '#178600',
        'PHP': '#4F5D95',
        'TypeScript': '#2b7489',
        'Ruby': '#701516',
        'Go': '#00ADD8',
        'Swift': '#ffac45',
        'Kotlin': '#F18E33',
        'Rust': '#dea584',
        'HTML': '#e34c26',
        'CSS': '#563d7c',
        'Shell': '#89e051'
    }
    
    # Calculate health score based on repository metrics
    health_score = min(100, max(0, 50 + 
                               (5 if repository.description else 0) + 
                               (10 if repository.stars > 10 else repository.stars) + 
                               (10 if repository.forks > 10 else repository.forks) + 
                               (5 if len(contributors) > 5 else len(contributors)) + 
                               (10 if len(commits) > 20 else len(commits) // 2)))
    
    # Calculate activity score based on commit frequency
    recent_commits = [c for c in commits if c.author_date and (datetime.utcnow() - c.author_date).days < 90]
    activity_score = min(100, max(0, 50 + 
                                 (30 if len(recent_commits) > 30 else len(recent_commits)) + 
                                 (10 if repository.updated_at and (datetime.utcnow() - repository.updated_at).days < 30 else 0)))
    
    # Calculate community score based on contributors and engagement
    community_score = min(100, max(0, 50 + 
                                  (25 if len(contributors) > 5 else len(contributors) * 5) + 
                                  (15 if repository.stars > 100 else repository.stars // 7) + 
                                  (10 if repository.forks > 10 else repository.forks)))
    
    # Format data for the template
    languages = {}
    if languages_data:
        total = sum(languages_data.values())
        if total > 0:
            languages = {lang: round((count / total) * 100, 1) for lang, count in languages_data.items()}
    
    # Format contributors for the template
    contributors_list = [{
        'username': c.username,
        'avatar_url': c.avatar_url,
        'html_url': c.html_url,
        'contributions': c.contributions
    } for c in contributors[:10]]  # Limit to top 10 contributors
    
    # Format commits for the template
    commits_list = [{
        'sha': c.sha[:7],  # Short SHA
        'message': c.message.split('\n')[0][:80] if c.message else '',  # First line of commit message
        'author_name': c.author_name,
        'author_date': c.author_date,
        'html_url': c.html_url
    } for c in commits[:20]]  # Limit to 20 most recent commits
    
    # Format commit activity for charts
    formatted_commit_activity = []
    if commit_activity:
        for week in commit_activity:
            if isinstance(week, dict) and 'week' in week and 'total' in week:
                date = datetime.fromtimestamp(week['week']).strftime('%Y-%m-%d')
                formatted_commit_activity.append({
                    'date': date,
                    'count': week['total']
                })
    
    # Current time for the template
    now = datetime.utcnow()
    
    return render_template(
        'results.html',
        repository=repository,
        contributors=contributors_list,
        commits=commits_list,
        commit_activity=formatted_commit_activity,
        languages=languages,
        language_colors=language_colors,
        health_score=health_score,
        activity_score=activity_score,
        community_score=community_score,
        repo_name=repository.name,
        repo_owner=repository.owner,
        repo_url=repository.html_url,
        repo_description=repository.description,
        stars=repository.stars,
        forks=repository.forks,
        open_issues=repository.open_issues,
        created_at=repository.created_at.strftime('%Y-%m-%d') if repository.created_at else '',
        last_updated=repository.updated_at.strftime('%Y-%m-%d') if repository.updated_at else '',
        now=now
    )

@app.route('/compare', methods=['POST'])
def compare_repositories():
    """Compare two GitHub repositories."""
    repo1_url = request.form.get('repo1', '')
    repo2_url = request.form.get('repo2', '')
    
    # Parse the repository URLs
    owner1, repo1 = github_api.parse_repo_url(repo1_url)
    owner2, repo2 = github_api.parse_repo_url(repo2_url)
    
    if not owner1 or not repo1 or not owner2 or not repo2:
        flash('Invalid GitHub repository URLs. Please enter valid URLs in the format "owner/repo" or "https://github.com/owner/repo".', 'danger')
        return redirect(url_for('index'))
    
    # Check if repositories exist in database
    repo1_obj = Repository.query.filter_by(owner=owner1, name=repo1).first()
    repo2_obj = Repository.query.filter_by(owner=owner2, name=repo2).first()
    
    # If repositories don't exist, analyze them first
    if not repo1_obj:
        return redirect(url_for('analyze_repository', repo_url=f"{owner1}/{repo1}"))
    
    if not repo2_obj:
        return redirect(url_for('analyze_repository', repo_url=f"{owner2}/{repo2}"))
    
    # Get repository data
    repo1_data = {
        'id': repo1_obj.id,
        'name': repo1_obj.name,
        'owner': repo1_obj.owner,
        'full_name': repo1_obj.full_name,
        'description': repo1_obj.description,
        'stars': repo1_obj.stars,
        'forks': repo1_obj.forks,
        'watchers': repo1_obj.watchers,
        'open_issues': repo1_obj.open_issues,
        'primary_language': repo1_obj.primary_language,
        'created_at': repo1_obj.created_at.strftime('%Y-%m-%d') if repo1_obj.created_at else '',
        'updated_at': repo1_obj.updated_at.strftime('%Y-%m-%d') if repo1_obj.updated_at else '',
        'size': repo1_obj.size,
        'health_score': min(100, max(0, 50 + 
                               (5 if repo1_obj.description else 0) + 
                               (10 if repo1_obj.stars > 10 else repo1_obj.stars) + 
                               (10 if repo1_obj.forks > 10 else repo1_obj.forks))),
        'activity_score': min(100, max(0, 50 + 
                                 (10 if repo1_obj.updated_at and (datetime.utcnow() - repo1_obj.updated_at).days < 30 else 0))),
        'community_score': min(100, max(0, 50 + 
                                  (15 if repo1_obj.stars > 100 else repo1_obj.stars // 7) + 
                                  (10 if repo1_obj.forks > 10 else repo1_obj.forks)))
    }
    
    repo2_data = {
        'id': repo2_obj.id,
        'name': repo2_obj.name,
        'owner': repo2_obj.owner,
        'full_name': repo2_obj.full_name,
        'description': repo2_obj.description,
        'stars': repo2_obj.stars,
        'forks': repo2_obj.forks,
        'watchers': repo2_obj.watchers,
        'open_issues': repo2_obj.open_issues,
        'primary_language': repo2_obj.primary_language,
        'created_at': repo2_obj.created_at.strftime('%Y-%m-%d') if repo2_obj.created_at else '',
        'updated_at': repo2_obj.updated_at.strftime('%Y-%m-%d') if repo2_obj.updated_at else '',
        'size': repo2_obj.size,
        'health_score': min(100, max(0, 50 + 
                               (5 if repo2_obj.description else 0) + 
                               (10 if repo2_obj.stars > 10 else repo2_obj.stars) + 
                               (10 if repo2_obj.forks > 10 else repo2_obj.forks))),
        'activity_score': min(100, max(0, 50 + 
                                 (10 if repo2_obj.updated_at and (datetime.utcnow() - repo2_obj.updated_at).days < 30 else 0))),
        'community_score': min(100, max(0, 50 + 
                                  (15 if repo2_obj.stars > 100 else repo2_obj.stars // 7) + 
                                  (10 if repo2_obj.forks > 10 else repo2_obj.forks)))
    }
    
    # Get contributors for both repositories
    repo1_contributors = Contributor.query.filter_by(repository_id=repo1_obj.id).order_by(Contributor.contributions.desc()).all()
    repo2_contributors = Contributor.query.filter_by(repository_id=repo2_obj.id).order_by(Contributor.contributions.desc()).all()
    
    # Get commits for both repositories
    repo1_commits = Commit.query.filter_by(repository_id=repo1_obj.id).order_by(Commit.author_date.desc()).all()
    repo2_commits = Commit.query.filter_by(repository_id=repo2_obj.id).order_by(Commit.author_date.desc()).all()
    
    # Render comparison template
    return render_template(
        'compare.html',
        repo1=repo1_data,
        repo2=repo2_data,
        repo1_contributors=repo1_contributors[:10],  # Limit to top 10
        repo2_contributors=repo2_contributors[:10],  # Limit to top 10
        repo1_commits=repo1_commits[:20],  # Limit to 20 most recent
        repo2_commits=repo2_commits[:20],  # Limit to 20 most recent
        now=datetime.utcnow()
    )

@app.route('/history')
def history():
    """View previously analyzed repositories."""
    page = request.args.get('page', 1, type=int)
    per_page = app.config.get('RESULTS_PER_PAGE', 10)
    
    repositories = Repository.query.order_by(Repository.last_analyzed.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('history.html', repositories=repositories)

@app.route('/api/repository/<int:repo_id>')
def api_repository(repo_id):
    """API endpoint for repository data."""
    repository = Repository.query.get_or_404(repo_id)
    contributors = Contributor.query.filter_by(repository_id=repo_id).order_by(Contributor.contributions.desc()).all()
    commits = Commit.query.filter_by(repository_id=repo_id).order_by(Commit.author_date.desc()).all()
    
    # Convert to dictionary
    repo_dict = {
        'id': repository.id,
        'name': repository.name,
        'owner': repository.owner,
        'full_name': repository.full_name,
        'description': repository.description,
        'html_url': repository.html_url,
        'stars': repository.stars,
        'forks': repository.forks,
        'watchers': repository.watchers,
        'open_issues': repository.open_issues,
        'primary_language': repository.primary_language,
        'created_at': repository.created_at.isoformat() if repository.created_at else None,
        'updated_at': repository.updated_at.isoformat() if repository.updated_at else None,
        'size': repository.size,
        'default_branch': repository.default_branch,
        'last_analyzed': repository.last_analyzed.isoformat(),
        'contributors': [
            {
                'username': c.username,
                'avatar_url': c.avatar_url,
                'html_url': c.html_url,
                'contributions': c.contributions
            } for c in contributors
        ],
        'commits': [
            {
                'sha': c.sha,
                'message': c.message,
                'author_name': c.author_name,
                'author_date': c.author_date.isoformat() if c.author_date else None,
                'html_url': c.html_url
            } for c in commits[:20]  # Limit to 20 commits
        ]
    }
    
    return jsonify(repo_dict)

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
