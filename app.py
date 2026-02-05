import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

app = Flask(__name__)

# --- CONFIGURAÇÕES DE ALTA SEGURANÇA ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_mb_energy_key_2026')
uri = os.environ.get('DATABASE_URL', 'sqlite:///mb_energy.db')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS ESCALÁVEIS ---

class User(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    device_id = db.Column(db.String(100), unique=True, index=True) # Indexado para performance

class ConsumoHistorico(db.Model):
    __tablename__ = 'historico_consumo'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), index=True, nullable=False)
    setor = db.Column(db.String(50), nullable=False)
    watts = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), index=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROTAS DE PRODUÇÃO ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Acesso negado. Verifique suas credenciais.')
    return render_template('login.html')

@app.route('/')
@login_required
def dashboard():
    # Lógica Avançada: Pega a última leitura de cada setor disponível
    subquery = db.session.query(
        ConsumoHistorico.setor,
        db.func.max(ConsumoHistorico.timestamp).label('max_ts')
    ).filter(ConsumoHistorico.device_id == current_user.device_id).group_by(ConsumoHistorico.setor).subquery()

    dados_atuais = db.session.query(ConsumoHistorico).join(
        subquery, (ConsumoHistorico.setor == subquery.c.setor) & (ConsumoHistorico.timestamp == subquery.c.max_ts)
    ).all()

    setores = [d.setor for d in dados_atuais]
    valores = [d.watts for d in dados_atuais]
    total_watts = sum(valores)
    
    # Projeção Inteligente (Tarifa Salvador/BA média R$ 0,90)
    custo_mensal = (total_watts / 1000) * 0.90 * 24 * 30

    return render_template('dashboard.html', 
                           name=current_user.username,
                           device=current_user.device_id,
                           setores=setores if setores else ["Aguardando..."],
                           valores=valores if valores else [0],
                           total=round(total_watts, 2),
                           custo=round(custo_mensal, 2))

@app.route('/api/sensor-data', methods=['POST'])
def sensor_inbound():
    data = request.get_json()
    if not data or 'device_id' not in data:
        return jsonify({"status": "error", "message": "Payload inválido"}), 400
    
    # Validação de Dispositivo
    if not User.query.filter_by(device_id=data['device_id']).first():
        return jsonify({"status": "unauthorized"}), 401

    for key, value in data.items():
        if key != 'device_id':
            db.session.add(ConsumoHistorico(device_id=data['device_id'], setor=key, watts=float(value)))
    
    db.session.commit()
    return jsonify({"status": "success"}), 201

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
