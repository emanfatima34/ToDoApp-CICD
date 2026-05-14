import os
import pymysql
from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_session import Session

application = Flask(__name__)
application.secret_key = "secret123"
application.config["SESSION_TYPE"] = "filesystem"
application.config["SESSION_PERMANENT"] = False
application.config["SESSION_COOKIE_NAME"] = "taskmaster_session"
application.config["SESSION_COOKIE_HTTPONLY"] = True
Session(application)

# Database credentials from environment variables
DB_HOST = os.environ.get("DB_HOST", "db")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "mypassword123")
DB_NAME = os.environ.get("DB_NAME", "todoapp")

# Database connection function with retry logic
def get_db_connection():
    import time
    max_retries = 30  # Increased from 5 to 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = pymysql.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                cursorclass=pymysql.cursors.DictCursor
            )
            print("Database connected successfully!")
            return conn
        except pymysql.err.OperationalError as e:
            retry_count += 1
            if retry_count < max_retries:
                print(f"Database connection failed. Retrying ({retry_count}/{max_retries})... waiting 3 seconds")
                time.sleep(3)  # Increased from 2 to 3 seconds
            else:
                print(f"Failed to connect to database after {max_retries} attempts")
                raise

# Initialize database when not running import-only unit tests on the CI host.
# Jenkins runs unittest on the VM: hostname "db" only exists on the Docker Compose network.
_skip_db_at_import = os.environ.get("SKIP_DB_AT_IMPORT", "").strip().lower() in ("1", "true", "yes")
db_conn = None
cursor = None

if not _skip_db_at_import:
    try:
        db_conn = get_db_connection()
    except Exception:
        db_conn = None
    if db_conn is not None:
        cursor = db_conn.cursor()
        cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username VARCHAR(50) PRIMARY KEY,
    password VARCHAR(100) NOT NULL
)
""")
        cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    title VARCHAR(100),
    description TEXT,
    dueDate DATE,
    priority VARCHAR(10),
    completed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (username) REFERENCES users(username)
)
""")
        db_conn.commit()

# ===================== DASHBOARD HTML =====================
dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TaskMaster - Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
}
.wrapper { max-width: 1200px; margin: auto; }
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 30px;
    background: white;
    padding: 25px 30px;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}
h1 { 
    color: #333; 
    font-size: 2em;
    margin: 0;
}
.user-info {
    display: flex;
    align-items: center;
    gap: 20px;
}
.user-badge {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.9em;
}
.logout-btn {
    background: #f5576c;
    color: white;
    text-decoration: none;
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.3s ease;
    cursor: pointer;
    border: none;
    font-size: 0.95em;
}
.logout-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(245, 87, 108, 0.4);
    background: #e63e50;
}
.nav-tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 30px;
}
.nav-btn {
    padding: 12px 30px;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    cursor: pointer;
    font-size: 1em;
    transition: all 0.3s ease;
    text-decoration: none;
    display: inline-block;
    background: white;
    color: #333;
}
.nav-btn.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}
.nav-btn:hover:not(.active) {
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
}
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}
.stat-card {
    background: white;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    text-align: center;
    transition: transform 0.3s ease;
}
.stat-card:hover {
    transform: translateY(-5px);
}
.stat-icon {
    font-size: 2.5em;
    margin-bottom: 15px;
}
.stat-value {
    font-size: 2.5em;
    font-weight: 700;
    color: #333;
    margin-bottom: 10px;
}
.stat-label {
    color: #666;
    font-size: 1em;
    font-weight: 500;
}
.progress-section {
    background: white;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    margin-bottom: 30px;
}
.progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}
.progress-header h2 {
    color: #333;
    margin: 0;
    font-size: 1.5em;
}
.progress-percentage {
    font-size: 1.8em;
    font-weight: 700;
    color: #667eea;
}
.progress-bar-container {
    width: 100%;
    height: 25px;
    background: #e0e0e0;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 15px;
}
.progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    transition: width 0.5s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 600;
    font-size: 0.9em;
}
.progress-details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 20px;
}
.progress-detail-item {
    display: flex;
    align-items: center;
    gap: 15px;
}
.progress-detail-icon {
    width: 50px;
    height: 50px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8em;
}
.completed-icon {
    background: #d4edda;
}
.progress-icon {
    background: #fff3cd;
}
.progress-detail-text h3 {
    margin: 0;
    color: #333;
    font-size: 1.1em;
}
.progress-detail-text p {
    margin: 5px 0 0 0;
    color: #666;
    font-size: 0.9em;
}
.tasks-preview {
    background: white;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}
.tasks-preview h2 {
    color: #333;
    margin-bottom: 20px;
    font-size: 1.5em;
}
.quick-task-list {
    list-style: none;
}
.quick-task-item {
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 15px;
    background: #f8f9fa;
    border-left: 4px solid #667eea;
    margin-bottom: 12px;
    border-radius: 8px;
}
.quick-task-item.completed {
    opacity: 0.6;
    background: #f0f0f0;
}
.task-checkbox {
    width: 20px;
    height: 20px;
    cursor: pointer;
}
.task-info {
    flex: 1;
    overflow: hidden;
}
.task-title {
    font-weight: 600;
    color: #333;
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.quick-task-item.completed .task-title {
    text-decoration: line-through;
    color: #999;
}
.task-meta {
    font-size: 0.85em;
    color: #666;
    margin: 5px 0 0 0;
}
.priority-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 600;
}
.priority-low { background: #d4edda; color: #155724; }
.priority-medium { background: #fff3cd; color: #856404; }
.priority-high { background: #f8d7da; color: #721c24; }
.view-all-btn {
    display: inline-block;
    margin-top: 20px;
    padding: 12px 30px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    text-decoration: none;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.3s ease;
}
.view-all-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}
.empty-message {
    text-align: center;
    padding: 40px;
    color: #999;
}
.empty-message p {
    font-size: 1.1em;
    margin: 10px 0;
}
</style>
</head>
<body>
<div class="wrapper">
    <div class="header">
        <h1>📊 TaskMaster Dashboard</h1>
        <div class="user-info">
            <span class="user-badge">👤 {{ user }}</span>
            <form method="GET" action="{{ url_for('logout') }}" style="margin: 0;">
                <button type="submit" class="logout-btn">Logout</button>
            </form>
        </div>
    </div>

    <div class="nav-tabs">
        <a href="{{ url_for('dashboard') }}" class="nav-btn active">📊 Dashboard</a>
        <a href="{{ url_for('tasks_page') }}" class="nav-btn">📋 My Tasks</a>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-icon">📝</div>
            <div class="stat-value">{{ total }}</div>
            <div class="stat-label">Total Tasks</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">✅</div>
            <div class="stat-value">{{ completed }}</div>
            <div class="stat-label">Completed</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">⏳</div>
            <div class="stat-value">{{ in_progress }}</div>
            <div class="stat-label">In Progress</div>
        </div>
    </div>

    <div class="progress-section">
        <div class="progress-header">
            <h2>📈 Overall Progress</h2>
            <div class="progress-percentage">{{ "%.0f"|format(progress) }}%</div>
        </div>
        <div class="progress-bar-container">
            <div class="progress-bar-fill" style="width: {{ progress }}%;">
                {% if progress > 10 %}{{ "%.0f"|format(progress) }}%{% endif %}
            </div>
        </div>
        <div class="progress-details">
            <div class="progress-detail-item">
                <div class="progress-detail-icon completed-icon">✅</div>
                <div class="progress-detail-text">
                    <h3>{{ completed }} Completed</h3>
                    <p>Tasks finished successfully</p>
                </div>
            </div>
            <div class="progress-detail-item">
                <div class="progress-detail-icon progress-icon">⏳</div>
                <div class="progress-detail-text">
                    <h3>{{ in_progress }} In Progress</h3>
                    <p>Tasks waiting to be completed</p>
                </div>
            </div>
        </div>
    </div>

    <div class="tasks-preview">
        <h2>📋 Recent Tasks</h2>
        {% if user_tasks %}
        <ul class="quick-task-list">
        {% for t in user_tasks[:5] %}
            <li class="quick-task-item {% if t['completed'] %}completed{% endif %}">
                <input type="checkbox" class="task-checkbox" {% if t['completed'] %}checked disabled{% endif %}>
                <div class="task-info">
                    <p class="task-title">{{ t['title'] }}</p>
                    <p class="task-meta">
                        <span class="priority-badge priority-{{ t['priority'].lower() }}">{{ t['priority'] }}</span>
                        {% if t['dueDate'] %}&nbsp;📅 {{ t['dueDate'] }}{% endif %}
                    </p>
                </div>
            </li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('tasks_page') }}" class="view-all-btn">View All Tasks →</a>
        {% else %}
        <div class="empty-message">
            <p>✨ No tasks yet!</p>
            <p><a href="{{ url_for('tasks_page') }}" style="color: #667eea; text-decoration: none; font-weight: 600;">Create your first task →</a></p>
        </div>
        {% endif %}
    </div>
</div>
</body>
</html>
"""

# ----------------- HTML Templates -----------------
welcome_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TaskMaster - Home</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    display: flex; 
    justify-content: center; 
    align-items: center; 
    height: 100vh; 
    overflow: hidden;
}
.container { 
    background: white; 
    padding: 80px 60px; 
    border-radius: 20px; 
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); 
    text-align: center;
    max-width: 500px;
    animation: slideUp 0.6s ease-out;
}
@keyframes slideUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}
h1 { 
    color: #333; 
    font-size: 3em; 
    margin-bottom: 15px; 
    font-weight: 700;
}
.subtitle {
    color: #666;
    font-size: 1.2em;
    margin-bottom: 50px;
    font-weight: 300;
}
.button-group {
    display: flex;
    flex-direction: column;
    gap: 15px;
}
a {
    text-decoration: none;
    padding: 18px 40px;
    color: white;
    border-radius: 12px;
    font-weight: 600;
    font-size: 1.1em;
    transition: all 0.3s ease;
    display: inline-block;
}
.welcome-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
}
.welcome-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 15px 35px rgba(102, 126, 234, 0.6);
}
.signup-btn {
    background: #f093fb;
    box-shadow: 0 10px 25px rgba(240, 147, 251, 0.4);
}
.signup-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 15px 35px rgba(240, 147, 251, 0.6);
    background: #e87eea;
}
.features {
    margin-top: 60px;
    text-align: left;
    padding-top: 30px;
    border-top: 2px solid #eee;
}
.feature-item {
    display: flex;
    align-items: center;
    margin: 15px 0;
    color: #555;
}
.feature-item::before {
    content: "✓";
    display: inline-block;
    width: 30px;
    height: 30px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 50%;
    text-align: center;
    line-height: 30px;
    margin-right: 12px;
    font-weight: bold;
    flex-shrink: 0;
}
</style>
</head>
<body>
<div class="container">
    <h1>📝 TaskMaster</h1>
    <p class="subtitle">Organize your life, one task at a time</p>
    
    <div class="button-group">
        <a href="{{ url_for('register') }}" class="welcome-btn">Welcome! Get Started</a>
        <a href="{{ url_for('login') }}" class="signup-btn">Already have an account?</a>
    </div>
    
    <div class="features">
        <div class="feature-item">Create and manage your tasks</div>
        <div class="feature-item">Set priorities and due dates</div>
        <div class="feature-item">Track your progress easily</div>
    </div>
</div>
</body>
</html>
"""

register_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Create Account</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    display: flex; 
    justify-content: center; 
    align-items: center; 
    height: 100vh;
    overflow: hidden;
}
.container { 
    background: white; 
    padding: 50px; 
    border-radius: 20px; 
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); 
    width: 100%;
    max-width: 400px;
    animation: slideUp 0.6s ease-out;
}
@keyframes slideUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}
h2 { 
    text-align: center; 
    margin-bottom: 30px; 
    color: #333;
    font-size: 2em;
}
.form-group {
    margin-bottom: 15px;
}
input { 
    width: 100%; 
    padding: 12px 15px; 
    margin-bottom: 8px; 
    border-radius: 8px; 
    border: 2px solid #e0e0e0;
    font-size: 1em;
    transition: border-color 0.3s ease;
}
input:focus {
    border-color: #f5576c;
    outline: none;
    background: #fff9fa;
}
button { 
    width: 100%; 
    padding: 12px; 
    margin-top: 10px;
    border-radius: 8px; 
    border: none; 
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: white; 
    font-weight: bold;
    font-size: 1.05em;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 5px 15px rgba(245, 87, 108, 0.3);
}
button:hover { 
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(245, 87, 108, 0.5);
}
.error { 
    color: #f5576c; 
    text-align: center;
    background: #ffe0e6;
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 15px;
    font-weight: 500;
}
p { 
    text-align: center; 
    margin-top: 20px; 
    color: #666;
}
a { 
    color: #f5576c; 
    text-decoration: none;
    font-weight: 600;
}
a:hover { 
    text-decoration: underline;
}
</style>
</head>
<body>
<div class="container">
    <h2>Create Account</h2>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <form method="POST">
        <div class="form-group">
            <input name="username" placeholder="Choose a username" required>
        </div>
        <div class="form-group">
            <input name="password" type="password" placeholder="Create a password" required>
        </div>
        <button type="submit">Sign Up</button>
    </form>
    <p>Already have an account? <a href="{{ url_for('login') }}">Login here</a></p>
</div>
</body>
</html>
"""

login_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Login</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    display: flex; 
    justify-content: center; 
    align-items: center; 
    height: 100vh;
    overflow: hidden;
}
.container { 
    background: white; 
    padding: 50px; 
    border-radius: 20px; 
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); 
    width: 100%;
    max-width: 400px;
    animation: slideUp 0.6s ease-out;
}
@keyframes slideUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}
h2 { 
    text-align: center; 
    margin-bottom: 30px; 
    color: #333;
    font-size: 2em;
}
.form-group {
    margin-bottom: 15px;
}
input { 
    width: 100%; 
    padding: 12px 15px; 
    margin-bottom: 8px; 
    border-radius: 8px; 
    border: 2px solid #e0e0e0;
    font-size: 1em;
    transition: border-color 0.3s ease;
}
input:focus {
    border-color: #667eea;
    outline: none;
    background: #f0f4ff;
}
button { 
    width: 100%; 
    padding: 12px; 
    margin-top: 10px;
    border-radius: 8px; 
    border: none; 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; 
    font-weight: bold;
    font-size: 1.05em;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}
button:hover { 
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(102, 126, 234, 0.5);
}
.error { 
    color: #f5576c; 
    text-align: center;
    background: #ffe0e6;
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 15px;
    font-weight: 500;
}
p { 
    text-align: center; 
    margin-top: 20px; 
    color: #666;
}
a { 
    color: #667eea; 
    text-decoration: none;
    font-weight: 600;
}
a:hover { 
    text-decoration: underline;
}
</style>
</head>
<body>
<div class="container">
    <h2>Login</h2>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <form method="POST">
        <div class="form-group">
            <input name="username" placeholder="Enter your username" required>
        </div>
        <div class="form-group">
            <input name="password" type="password" placeholder="Enter your password" required>
        </div>
        <button type="submit">Sign In</button>
    </form>
    <p>New user? <a href="{{ url_for('register') }}">Create an account</a></p>
</div>
</body>
</html>
"""

tasks_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TaskMaster - My Tasks</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
}
.wrapper { max-width: 1000px; margin: auto; }
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 30px;
    background: white;
    padding: 25px 30px;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}
h1 { 
    color: #333; 
    font-size: 2em;
    margin: 0;
}
.user-info {
    display: flex;
    align-items: center;
    gap: 20px;
}
.user-badge {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.9em;
}
.logout-btn {
    background: #f5576c;
    color: white;
    text-decoration: none;
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.3s ease;
    cursor: pointer;
    border: none;
    font-size: 0.95em;
}
.logout-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(245, 87, 108, 0.4);
    background: #e63e50;
}
.nav-tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 30px;
}
.nav-btn {
    padding: 12px 30px;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    cursor: pointer;
    font-size: 1em;
    transition: all 0.3s ease;
    text-decoration: none;
    display: inline-block;
    background: white;
    color: #333;
}
.nav-btn.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}
.nav-btn:hover:not(.active) {
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
}
.add-task-section {
    background: white;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    margin-bottom: 30px;
}
.add-task-section h2 {
    color: #333;
    margin-bottom: 20px;
    font-size: 1.5em;
}
.form-row {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr;
    gap: 15px;
}
input, textarea, select {
    padding: 12px 15px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 1em;
    font-family: inherit;
    transition: border-color 0.3s ease;
}
input:focus, textarea:focus, select:focus {
    border-color: #667eea;
    outline: none;
    background: #f0f4ff;
}
.form-group.full {
    grid-column: 1 / -1;
}
textarea { resize: vertical; min-height: 80px; }
.add-btn {
    grid-column: 1 / -1;
    padding: 12px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 1.05em;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}
.add-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(102, 126, 234, 0.5);
}
.tasks-section {
    background: white;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}
.tasks-section h2 {
    color: #333;
    margin-bottom: 20px;
    font-size: 1.5em;
}
.tasks-list { list-style: none; }
.task-card {
    background: #f8f9fa;
    border-left: 4px solid #667eea;
    padding: 20px;
    margin-bottom: 15px;
    border-radius: 10px;
    transition: all 0.3s ease;
}
.task-card:hover {
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
    transform: translateX(5px);
}
.task-card.completed {
    opacity: 0.6;
    background: #f0f0f0;
    border-left-color: #28a745;
}
.task-card.completed .task-title {
    text-decoration: line-through;
    color: #999;
}
.task-header {
    display: flex;
    justify-content: space-between;
    align-items: start;
    margin-bottom: 10px;
}
.task-title {
    font-size: 1.2em;
    font-weight: 600;
    color: #333;
    margin: 0;
    flex: 1;
}
.task-priority {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 600;
}
.priority-low { background: #d4edda; color: #155724; }
.priority-medium { background: #fff3cd; color: #856404; }
.priority-high { background: #f8d7da; color: #721c24; }
.task-description {
    color: #666;
    margin: 10px 0;
    font-size: 0.95em;
}
.task-due {
    color: #999;
    font-size: 0.9em;
    margin: 8px 0;
}
.task-actions {
    display: flex;
    gap: 10px;
    margin-top: 15px;
    flex-wrap: wrap;
}
.task-btn {
    padding: 8px 15px;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    font-size: 0.9em;
    transition: all 0.3s ease;
}
.edit-btn {
    background: #667eea;
    color: white;
}
.edit-btn:hover { background: #5568d3; }
.complete-btn {
    background: #28a745;
    color: white;
}
.complete-btn:hover { background: #218838; }
.delete-btn {
    background: #f5576c;
    color: white;
}
.delete-btn:hover { background: #e63e50; }
.empty-message {
    text-align: center;
    color: #999;
    padding: 40px;
    font-size: 1.1em;
}

.tasks-list-container {
    width: 100%;
}

{% for t in user_tasks %}
<div class="task-card {% if t['completed'] %}completed{% endif %}">
    <div class="task-header">
        <h3 class="task-title">{{ t['title'] }}</h3>
        <span class="task-priority priority-{{ t['priority'].lower() }}">{{ t['priority'] }}</span>
    </div>
    {% if t['description'] %}
    <p class="task-description">{{ t['description'] }}</p>
    {% endif %}
    {% if t['dueDate'] %}
    <p class="task-due">📅 Due: {{ t['dueDate'] }}</p>
    {% endif %}
    <div class="task-actions">
        <form method="POST" action="{{ url_for('toggle', task_id=t['id']) }}" style="display:inline;">
            <button type="submit" class="task-btn complete-btn">
                {{ 'Undo' if t['completed'] else 'Complete' }}
            </button>
        </form>
        <form method="POST" action="{{ url_for('delete', task_id=t['id']) }}" style="display:inline;">
            <button type="submit" class="task-btn delete-btn">Delete</button>
        </form>
    </div>
</div>
{% endfor %}
.modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    animation: fadeIn 0.3s ease;
}
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
.modal-content {
    background: white;
    margin: 10% auto;
    padding: 30px;
    border-radius: 15px;
    width: 90%;
    max-width: 500px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    animation: slideUp 0.3s ease;
}
@keyframes slideUp {
    from { transform: translateY(50px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}
.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}
.modal-header h2 {
    margin: 0;
    color: #333;
}
.close-btn {
    background: none;
    border: none;
    font-size: 28px;
    cursor: pointer;
    color: #999;
    transition: color 0.3s ease;
}
.close-btn:hover { color: #333; }
.modal-form-group {
    margin-bottom: 15px;
}
.modal-form-group label {
    display: block;
    margin-bottom: 8px;
    color: #333;
    font-weight: 500;
}
.modal-form-group input,
.modal-form-group textarea,
.modal-form-group select {
    width: 100%;
    padding: 10px 15px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-family: inherit;
    font-size: 1em;
}
.modal-form-group input:focus,
.modal-form-group textarea:focus,
.modal-form-group select:focus {
    border-color: #667eea;
    outline: none;
    background: #f0f4ff;
}
.modal-form-group textarea { resize: vertical; min-height: 80px; }
.modal-footer {
    display: flex;
    gap: 10px;
    margin-top: 20px;
}
.save-btn {
    flex: 1;
    padding: 12px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
}
.save-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(102, 126, 234, 0.5);
}
.cancel-btn {
    flex: 1;
    padding: 12px;
    background: #e0e0e0;
    color: #333;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
}
.cancel-btn:hover { background: #d0d0d0; }
</style>
<script>
function openEditModal(index) {
  document.getElementById("editModal" + index).style.display = "block";
}
function closeEditModal(index) {
  document.getElementById("editModal" + index).style.display = "none";
}
window.onclick = function(event) {
  if (event.target.classList.contains('modal')) {
    event.target.style.display = "none";
  }
}
</script>
</head>
<body>
<div class="wrapper">
    <div class="header">
        <h1>📋 My Tasks</h1>
        <div class="user-info">
            <span class="user-badge">👤 {{ user }}</span>
            <form method="GET" action="{{ url_for('logout') }}" style="margin: 0;">
                <button type="submit" class="logout-btn">Logout</button>
            </form>
        </div>
    </div>

    <div class="nav-tabs">
        <a href="{{ url_for('dashboard') }}" class="nav-btn">📊 Dashboard</a>
        <a href="{{ url_for('tasks_page') }}" class="nav-btn active">📋 My Tasks</a>
    </div>

    <div class="add-task-section">
        <h2>➕ Add New Task</h2>
        <form method="POST" action="{{ url_for('add') }}">
            <div class="form-row">
                <input name="title" placeholder="Enter task title..." required>
                <input type="date" name="dueDate">
                <select name="priority">
                    <option value="Low">Low Priority</option>
                    <option value="Medium" selected>Medium Priority</option>
                    <option value="High">High Priority</option>
                </select>
            </div>
            <div class="form-group full">
                <textarea name="description" placeholder="Add task description (optional)..."></textarea>
            </div>
            <button type="submit" class="add-btn">➕ Add Task</button>
        </form>
    </div>

    <div class="tasks-section">
        <h2>📋 All Tasks ({{ user_tasks|length }})</h2>
        {% if user_tasks %}
        <ul class="tasks-list">
        {% for t in user_tasks %}
            <li class="task-card {% if t['completed'] %}completed{% endif %}">
                <div class="task-header">
                    <h3 class="task-title">{{ t['title'] }}</h3>
                    <span class="task-priority priority-{{ t['priority'].lower() }}">{{ t['priority'] }}</span>
                </div>
                {% if t['description'] %}<p class="task-description">{{ t['description'] }}</p>{% endif %}
                {% if t['dueDate'] %}<p class="task-due">📅 Due: {{ t['dueDate'] }}</p>{% endif %}
                <div class="task-actions">
                    <button type="button" class="task-btn edit-btn" onclick="openEditModal({{ t['id'] }})">✏️ Edit</button>
                    <form method="POST" action="{{ url_for('toggle', task_id=t['id']) }}" style="display:inline;">
                        <button type="submit" class="task-btn {% if t['completed'] %}edit-btn{% else %}complete-btn{% endif %}">
                            {{ '↩️ Undo' if t['completed'] else '✓ Complete' }}
                        </button>
                    </form>
                    <form method="POST" action="{{ url_for('delete', task_id=t['id']) }}" style="display:inline;">
                        <button type="submit" class="task-btn delete-btn">🗑️ Delete</button>
                    </form>
                </div>
            </li>

            <div id="editModal{{ t['id'] }}" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>✏️ Edit Task</h2>
                        <button type="button" class="close-btn" onclick="closeEditModal({{ t['id'] }})">&times;</button>
                    </div>
                    <form method="POST" action="{{ url_for('edit', task_id=t['id']) }}">
                        <div class="modal-form-group">
                            <label>Task Title</label>
                            <input name="title" value="{{ t['title'] }}" required>
                        </div>
                        <div class="modal-form-group">
                            <label>Description</label>
                            <textarea name="description">{{ t['description'] }}</textarea>
                        </div>
                        <div class="modal-form-group">
                            <label>Due Date</label>
                            <input type="date" name="dueDate" value="{{ t['dueDate'] }}">
                        </div>
                        <div class="modal-form-group">
                            <label>Priority</label>
                            <select name="priority">
                                <option {% if t['priority'] == 'Low' %}selected{% endif %}>Low</option>
                                <option {% if t['priority'] == 'Medium' %}selected{% endif %}>Medium</option>
                                <option {% if t['priority'] == 'High' %}selected{% endif %}>High</option>
                            </select>
                        </div>
                        <div class="modal-footer">
                            <button type="submit" class="save-btn">💾 Save Changes</button>
                            <button type="button" class="cancel-btn" onclick="closeEditModal({{ t['id'] }})">Cancel</button>
                        </div>
                    </form>
                </div>
            </div>
        {% endfor %}
        </ul>
        {% else %}
        <div class="empty-message">
            <p>✨ No tasks yet!</p>
            <p>Create your first task above to get started.</p>
        </div>
        {% endif %}
    </div>
</div>
</body>
</html>
"""

# ----------------- ROUTES -----------------
@application.route("/")
def home():
    return render_template_string(welcome_html)

@application.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        u = request.form["username"]
        p = request.form["password"]
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE username=%s", (u,))
        if cursor.fetchone():
            return render_template_string(register_html, error="User already exists")
        
        # Insert new user
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (u, p))
        db_conn.commit()
        return redirect(url_for("login"))
    return render_template_string(register_html)

@application.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u = request.form["username"]
        p = request.form["password"]
        
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (u, p))
        user = cursor.fetchone()
        
        if user:
            session["username"] = u
            return redirect(url_for("dashboard"))
        return render_template_string(login_html, error="Invalid credentials")
    return render_template_string(login_html)

@application.route("/tasks")
def tasks_page():
    if "username" not in session:
        return redirect(url_for("login"))
    u = session["username"]
    
    cursor.execute("SELECT * FROM tasks WHERE username=%s", (u,))
    user_tasks = cursor.fetchall()
    
    return render_template_string(tasks_html, user=u, user_tasks=user_tasks)

@application.route("/add", methods=["POST"])
def add():
    u = session.get("username")
    if not u: return redirect(url_for("login"))
    
    cursor.execute("""
    INSERT INTO tasks (username, title, description, dueDate, priority)
    VALUES (%s, %s, %s, %s, %s)
    """, (
        u,
        request.form["title"],
        request.form.get("description", ""),
        request.form.get("dueDate", ""),
        request.form.get("priority", "Low")
    ))
    db_conn.commit()
    return redirect(url_for("tasks_page"))

@application.route("/edit/<int:task_id>", methods=["POST"])
def edit(task_id):
    u = session.get("username")
    if not u: return redirect(url_for("login"))
    
    cursor.execute("""
    UPDATE tasks 
    SET title=%s, description=%s, dueDate=%s, priority=%s
    WHERE id=%s AND username=%s
    """, (
        request.form["title"],
        request.form.get("description", ""),
        request.form.get("dueDate", ""),
        request.form.get("priority", "Low"),
        task_id,
        u
    ))
    db_conn.commit()
    return redirect(url_for("tasks_page"))

@application.route("/toggle/<int:task_id>", methods=["POST"])
def toggle(task_id):
    u = session.get("username")
    if not u: return redirect(url_for("login"))
    
    # Get current completed status
    cursor.execute("SELECT completed FROM tasks WHERE id=%s AND username=%s", (task_id, u))
    result = cursor.fetchone()
    if result:
        new_status = not result['completed']
        cursor.execute("UPDATE tasks SET completed=%s WHERE id=%s", (new_status, task_id))
        db_conn.commit()
    
    return redirect(url_for("tasks_page"))

@application.route("/delete/<int:task_id>", methods=["POST"])
def delete(task_id):
    u = session.get("username")
    if not u: return redirect(url_for("login"))
    
    cursor.execute("DELETE FROM tasks WHERE id=%s AND username=%s", (task_id, u))
    db_conn.commit()
    
    return redirect(url_for("tasks_page"))

@application.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("home"))

@application.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    u = session["username"]
    
    cursor.execute("SELECT * FROM tasks WHERE username=%s", (u,))
    user_tasks = cursor.fetchall()
    
    total = len(user_tasks)
    completed = len([t for t in user_tasks if t['completed']])
    in_progress = total - completed
    progress = (completed / total * 100) if total > 0 else 0
    
    return render_template_string(dashboard_html, user=u, total=total, completed=completed, in_progress=in_progress, progress=progress, user_tasks=user_tasks)

if __name__ == "__main__":
    application.run(debug=True, host="0.0.0.0", port=5000)