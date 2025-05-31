import os
from datetime import datetime
import logging
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Repository(db.Model):
    """Repository model for storing GitHub repository data."""
    __tablename__ = 'repositories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner = db.Column(db.String(100), nullable=False)
    full_name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    html_url = db.Column(db.String(255), nullable=False)
    api_url = db.Column(db.String(255), nullable=False)
    stars = db.Column(db.Integer, default=0)
    forks = db.Column(db.Integer, default=0)
    watchers = db.Column(db.Integer, default=0)
    open_issues = db.Column(db.Integer, default=0)
    primary_language = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)
    size = db.Column(db.Integer, default=0)
    default_branch = db.Column(db.String(100), default='main')
    last_analyzed = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    contributors = db.relationship('Contributor', backref='repository', lazy=True, cascade='all, delete-orphan')
    commits = db.relationship('Commit', backref='repository', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Repository {self.full_name}>'


class Contributor(db.Model):
    """Contributor model for storing repository contributor data."""
    __tablename__ = 'contributors'
    
    id = db.Column(db.Integer, primary_key=True)
    repository_id = db.Column(db.Integer, db.ForeignKey('repositories.id'), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)
    html_url = db.Column(db.String(255), nullable=True)
    contributions = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Contributor {self.username} for {self.repository.full_name}>'


class Commit(db.Model):
    """Commit model for storing repository commit data."""
    __tablename__ = 'commits'
    
    id = db.Column(db.Integer, primary_key=True)
    repository_id = db.Column(db.Integer, db.ForeignKey('repositories.id'), nullable=False)
    sha = db.Column(db.String(40), nullable=False)
    message = db.Column(db.Text, nullable=True)
    author_name = db.Column(db.String(100), nullable=True)
    author_email = db.Column(db.String(100), nullable=True)
    author_date = db.Column(db.DateTime, nullable=True)
    committer_name = db.Column(db.String(100), nullable=True)
    committer_email = db.Column(db.String(100), nullable=True)
    committer_date = db.Column(db.DateTime, nullable=True)
    html_url = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f'<Commit {self.sha[:7]} for {self.repository.full_name}>'


# Create function to initialize database
def init_db(app):
    """Initialize the database with the Flask app."""
    db.init_app(app)
    
    # Create tables if they don't exist
    with app.app_context():
        try:
            # Ensure instance directory exists
            instance_path = os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
            if instance_path and not os.path.exists(instance_path):
                os.makedirs(instance_path, exist_ok=True)
                logging.info(f"Created database directory: {instance_path}")
            
            # Create all tables
            logging.info("Creating database tables...")
            db.create_all()
            logging.info("Database tables created successfully.")
                
        except Exception as e:
            logging.error(f"Error initializing database: {str(e)}")
            raise
