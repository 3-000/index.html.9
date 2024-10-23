from flask import Flask, request, jsonify, render_template, session as flask_session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import os

app = Flask(__name__)

# Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['JWT_SECRET_KEY'] = ['jwt_secret_key']  # Set JWT secret key

# Extensions Initialization
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)
CORS(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Float, default=0)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='user1').first():
            user1 = User(username='user1')
            user1.set_password('password1')
            user1.balance = 10000000000000000
            db.session.add(user1)
            db.session.commit()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

# Signup Route
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return 'User already exists', 400

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return 'User created successfully', 201

# Login Route (returns JWT)
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        access_token = create_access_token(identity=user.id)
        return jsonify({
            'access_token': access_token,
            'balance': user.balance
        }), 200
    else:
        return 'Login failed', 401

# Protected Deposit Route
@app.route('/api/deposit', methods=['POST'])
@jwt_required()  # Protect this route with JWT
def deposit():
    user_id = get_jwt_identity()
    from_user = User.query.get(user_id)

    data = request.get_json()
    to_account_username = data.get('toAccount')
    amount = data.get('amount')

    if not amount or float(amount) <= 0:
        return 'Invalid deposit amount', 400

    to_user = User.query.filter_by(username=to_account_username).first()

    if not to_user:
        return 'Recipient account does not exist', 404

    if from_user.balance >= float(amount):
        from_user.balance -= float(amount)
        to_user.balance += float(amount)
        db.session.commit()

        return jsonify({
            'message': 'Deposit successful',
            'from_balance': from_user.balance,
            'to_balance': to_user.balance
        }), 200
    else:
        return 'Insufficient balance for the deposit', 400

# Serve Static Files
@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory('public', path)

# Initialize the database
init_db()

if __name__ == '__main__':
    app.run(port=3000)


