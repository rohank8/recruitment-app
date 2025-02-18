from flask import Flask, render_template
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
auth = HTTPBasicAuth()

# Configure credentials
users = {
    "admin": generate_password_hash("securepassword123")
}

@auth.verify_password
def verify_password(username, password):
    if username in users:
        return check_password_hash(users.get(username), password)
    return False

@app.route('/')
@auth.login_required
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)