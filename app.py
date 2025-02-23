from flask import Flask, render_template, request, redirect, url_for, flash
from kaggle_search import KaggleScraper
import os
from github_search import GitHubSearch
from threading import Thread
from flask import make_response
from functools import wraps
# Initialize app FIRST
app = Flask(__name__, static_url_path='/proxy/5000/static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-123')
app.config['APPLICATION_ROOT'] = '/proxy/5000'
app.config['PREFERRED_URL_SCHEME'] = 'https'

def add_colab_headers(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        # Modern security headers
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self' https://*.googleusercontent.com"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    return decorated_function

# Apply to all routes using after_request
@app.after_request
def apply_colab_headers(response):
    response = add_colab_headers(lambda: response)(*request.view_args)
    return response
# Apply to all routes using after_request
@app.after_request
def apply_colab_headers(response):
    response = add_colab_headers(lambda: response)(*request.view_args)
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/proxy/5000/search/github', methods=['GET'])
def github_search():
    try:
        search_term = request.args.get('q', '').strip()
        page = int(request.args.get('page', 1))
        
        if not search_term:
            flash('Please enter a search term', 'warning')
            return redirect(url_for('index'))
            
        searcher = GitHubSearch()
        results = searcher.search_users(search_term, page)
        
        if results['total_pages'] > page:
            for next_page in range(page + 1, min(page + 3, results['total_pages'] + 1)):
                Thread(target=searcher.search_users, args=(search_term, next_page)).start()
        
        return render_template('github_results.html',
                             results=results,
                             search_term=search_term)
                             
    except Exception as e:
        flash(f'Search failed: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/proxy/5000/search/kaggle', methods=['POST'])
def kaggle_search():
    scraper = KaggleScraper()
    try:
        url = request.form['url']
        results = scraper.scrape_leaderboard(url)
        return render_template('kaggle_results.html',
                            users=results,
                            search_term=url)
    except Exception as e:
        flash(f'Scraping failed: {str(e)}', 'danger')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
