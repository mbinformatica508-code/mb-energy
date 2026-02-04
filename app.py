import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

app = Flask(__name__)

# --- CONFIGURAÇÕES DE PRODUÇÃO (MB CIRCUITO DIGITAL) ---
# O sistema busca automaticamente as chaves do ambiente do servidor
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-de-seguranca-padrao-mb')

# Ajuste automático da URL do PostgreSQL (Neon/Koyeb)
uri = os.environ.get('DATABASE_URL', 'sqlite:///mb_energy.db')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS DE BANCO DE DADOS ---

class User(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    device_id = db.Column(db.String(100), unique=True, nullable=True)

class ConsumoHistorico(db.Model):
    __tablename__ = 'historico_consumo'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), index=True, nullable=False)
    setor = db.Column(db.String(50), nullable=False)
    watts = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROTAS DE AUTENTICAÇÃO ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Credenciais incorretas. Tente novamente.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- DASHBOARD DINÂMICO ---

@app.route('/')
@login_required
def dashboard():
    # Busca a última leitura de cada setor para o dispositivo do usuário logado
    subquery = db.session.query(
        ConsumoHistorico.setor,
        db.func.max(ConsumoHistorico.timestamp).label('max_ts')
    ).filter(ConsumoHistorico.device_id == current_user.device_id).group_by
    
