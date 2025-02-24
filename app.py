from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from kaggle_search import KaggleScraper
from github_search import GitHubSearch
from concurrent.futures import ThreadPoolExecutor
import os
import uuid

# Initialize app
app = Flask(__name__, static_url_path='/static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-123')

# Configure for Ngrok
app.config['PREFERRED_URL_SCHEME'] = 'https'
app.config['SERVER_NAME'] = 'localhost:5000'

# Background task setup
executor = ThreadPoolExecutor(4)
jobs = {}

# Security headers middleware
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self' https://*.googleusercontent.com"
    response.headers['X-Frame-Options'] = 'ALLOW-FROM https://colab.research.google.com'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/debug/github')
def debug_github():
    searcher = GitHubSearch()
    test_results = searcher.search_users("citadel", 1)
    return jsonify({
        "api_response": test_results,
        "env_token": os.environ.get('GITHUB_TOKEN', 'MISSING')
    })

@app.route('/search/github', methods=['GET'])
def github_search():
    try:
        search_term = request.args.get('q', '').strip()
        page = int(request.args.get('page', 1))
        
        if not search_term:
            flash('Please enter a search term', 'warning')
            return redirect(url_for('index'))
            
        job_id = str(uuid.uuid4())
        searcher = GitHubSearch()
        
        # Submit to background thread
        future = executor.submit(
            searcher.search_users,
            search_term,
            page
        )
        jobs[job_id] = future
        
        return render_template('loading.html', 
                            job_id=job_id,
                            search_type='github')
                             
    except Exception as e:
        flash(f'Search failed: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/search/kaggle', methods=['POST'])
def kaggle_search():
    try:
        url = request.form['url']
        job_id = str(uuid.uuid4())
        
        # Submit to background thread
        future = executor.submit(KaggleScraper().scrape_leaderboard, url)
        jobs[job_id] = future
        
        return render_template('loading.html', 
                            job_id=job_id,
                            search_type='kaggle')
        
    except Exception as e:
        flash(f'Scraping failed: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/search/status/<job_id>')
def check_status(job_id):
    if job_id not in jobs:
        return jsonify({'status': 'error', 'message': 'Invalid job ID'})
    
    future = jobs[job_id]
    if future.done():
        try:
            result = future.result()
            del jobs[job_id]
            return jsonify({'status': 'complete', 'result': result})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'processing'})

@app.route('/github-results')
def github_results():
    try:
        data = request.args.get('data')
        results = eval(data) if data else None
        return render_template('github_results.html',
                            results=results,
                            search_term=request.args.get('q', ''))
    except Exception as e:
        flash(f'Error loading results: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/search/kaggle/results')
def kaggle_results():
    try:
        data = request.args.get('data')
        results = eval(data)  # Caution: Only use with trusted data
        return render_template('kaggle_results.html',
                            users=results,
                            search_term="Kaggle Leaderboard")
    except:
        flash('Error loading results', 'danger')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
