import sqlite3
import os

def check_database(db_path):
    """Check the database structure and contents."""
    print(f"Checking database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("\nTables:")
        for table in tables:
            print(f"- {table[0]}")
            
        # Check repositories
        if ('repositories',) in tables:
            cursor.execute("SELECT id, owner, name, full_name, stars, forks, last_analyzed FROM repositories")
            repos = cursor.fetchall()
            print(f"\nRepositories ({len(repos)}):")
            for repo in repos:
                print(f"- ID: {repo[0]}, Owner: {repo[1]}, Name: {repo[2]}, Full Name: {repo[3]}")
                print(f"  Stars: {repo[4]}, Forks: {repo[5]}, Last Analyzed: {repo[6]}")
                
            # Check contributors for each repository
            for repo in repos:
                cursor.execute("SELECT COUNT(*) FROM contributors WHERE repository_id = ?", (repo[0],))
                contributor_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM commits WHERE repository_id = ?", (repo[0],))
                commit_count = cursor.fetchone()[0]
                
                print(f"  Contributors: {contributor_count}, Commits: {commit_count}")
        
        conn.close()
        print("\nDatabase check completed successfully.")
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Check both the main database and test database
    check_database("github_repos.db")
    check_database("test_github_analyzer.db")
