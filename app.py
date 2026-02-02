import os
from flask import Flask, render_template_string, jsonify, request, redirect, url_for, make_response
import random
from datetime import datetime

app = Flask(__name__)

dados_app = {
    "limite_gasto": 300.00,
    "picos": [],
    "assinaturas": {}
}

# --- LÓGICA DO PWA (MANIFESTO E SERVICE WORKER) ---
@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "MB Energy Intelligence",
        "short_name": "MB Energy",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0d1117",
        "theme_color": "#00aaff",
        "icons": [
            {
                "src": "https://cdn-icons-png.flaticon.com/512/2731/2731636.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

@app.route('/sw.js')
def sw():
    response = make_response("self.addEventListener('fetch', function(event) {});")
    response.headers['Content-Type'] = 'application/javascript'
    return response

# --- HTML PRINCIPAL ATUALIZADO ---
HTML_GERAL = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#00aaff">
    <title>MB Energy Intelligence</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root { --bg: #0d1117; --card: #161b22; --accent: #00aaff; --success: #238636; --danger: #da3633; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: white; margin: 0; padding: 15px; -webkit-tap-highlight-color: transparent; }
        .container { max-width: 500px; margin: auto; }
        .logo-container { text-align: center; margin-bottom: 10px; padding-top: 10px; }
        .logo-svg { width: 100px; height: auto; }
        .card { background: var(--card); padding: 20px; border-radius: 16px; margin-bottom: 15px; border: 1px solid #30363d; box-shadow: 0 4px 15px rgba(0,0,0,0.4); }
        .valor-principal { font-size: 32px; font-weight: bold; color: var(--success); }
        .watts { font-size: 42px; color: var(--accent); font-weight: bold; text-shadow: 0 0 10px rgba(0,170,255,0.2); }
        .label { font-size: 10px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
        .btn { background: var(--accent); color: white; padding: 16px; border-radius: 12px; text-decoration: none; display: block; text-align: center; font-weight: bold; border: none; font-size: 14px; }
        .alerta-box { background: rgba(218, 54, 51, 0.2); border: 1px solid var(--danger); color: #ff7b72; padding: 12px; border-radius: 8px; display: none; margin-bottom: 15px; text-align: center; font-weight: bold; }
        .pico-item { font-size: 13px; border-bottom: 1px solid #30363d; padding: 12px 0; display: flex; justify-content: space-between; align-items: center; }
        .btn-nomear { background: transparent; border: 1px solid var(--accent); color: var(--accent); padding: 6px 12px; border-radius: 6px; font-size: 10px; font-weight: bold; }
        .aparelho-nome { color: #ffa657; font-weight: bold; background: rgba(255,166,87,0.1); padding: 3px 8px; border-radius: 5px; font-size: 11px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-container">
            <svg class="logo-svg" viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg">
                <path d="M40 10 L25 45 L45 45 L30 75 L70 35 L50 35 L65 10 Z" fill="#00aaff" />
                <text x="80" y="55" font-family="Arial Black" font-size="50" fill="white">MB</text>
            </svg>
            <p style="font-size: 12px; color: #8b949e; margin-top: -5px; letter-spacing: 3px;">CIRCUITO DIGITAL</p>
        </div>

        <div class="card" style="text-align: center;">
            <div id="alerta_ui" class="alerta-box">⚠️ ALERTA DE CONSUMO CRÍTICO</div>
            <p class="label">Potência Atual</p>
            <div class="watts" id="potencia">0 W</div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div class="card">
                <p class="label">Projeção da Fatura</p>
                <div class="valor-principal" id="fatura">R$ 0,00</div>
            </div>
            <div class="card">
                <p class="label">Meta de Gasto</p>
                <div class="valor-principal" style="color: #c9d1d9;">R$ {{ "%.2f"|format(limite_atual) }}</div>
            </div>
        </div>

        <div class="card">
            <canvas id="grafico"></canvas>
        </div>

        <div class="card">
            <p class="label">Identificação Inteligente de Cargas</p>
            <div id="lista_picos"></div>
        </div>

        <a href="/configurar" class="btn">⚙️ CONFIGURAÇÕES DO SISTEMA</a>
    </div>

    <script>
        // Registro do Service Worker para o PWA
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js');
        }

        let meta = {{ limite_atual }};
        const ctx = document.getElementById('grafico').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Watts', data: [], borderColor: '#00aaff', tension: 0.4, fill: true, backgroundColor: 'rgba(0, 170, 255, 0.05)' }] },
            options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#1f242c' } }, x: { display: false } } }
        });

        function nomearAparelho(valor) {
            let nome = prompt("Identificar carga de " + valor + "W como:");
            if (nome) {
                fetch('/api/nomear', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({valor: valor, nome: nome})
                }).then(() => atualizar());
            }
        }

        function atualizar() {
            fetch('/api/dados')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('potencia').innerText = data.potencia + " W";
                    document.getElementById('fatura').innerText = "R$ " + data.fatura;
                    
                    const valorNum = parseFloat(data.fatura.replace(',','.'));
                    if (valorNum > meta) {
                        document.getElementById('alerta_ui').style.display = 'block';
                        // Aqui o Google enviaria a notificação push no futuro
                    } else {
                        document.getElementById('alerta_ui').style.display = 'none';
                    }

                    if (chart.data.labels.length > 15) { chart.data.labels.shift(); chart.data.datasets[0].data.shift(); }
                    chart.data.labels.push(new Date().toLocaleTimeString());
                    chart.data.datasets[0].data.push(data.potencia);
                    chart.update();

                    let html = '';
                    data.picos.forEach(p => {
                        let iden = p.nome ? `<span class="aparelho-nome">${p.nome}</span>` : `<button class="btn-nomear" onclick="nomearAparelho(${p.valor})">IDENTIFICAR</button>`;
                        html += `<div class="pico-item"><span>${p.hora} • <strong>${p.valor}W</strong></span>${iden}</div>`;
                    });
                    document.getElementById('lista_picos').innerHTML = html;
                });
        }
        setInterval(atualizar, 3000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_GERAL, limite_atual=dados_app["limite_gasto"])

@app.route('/configurar', methods=['GET', 'POST'])
def configurar():
    if request.method == 'POST':
        dados_app["limite_gasto"] = float(request.form.get('limite'))
        return redirect(url_for('index'))
    return render_template_string("""
        <body style="background:#0d1117;color:white;font-family:sans-serif;text-align:center;padding:50px;">
            <h2 style="color:#00aaff">Ajustar Limites</h2>
            <form method="POST">
                <input type="number" step="0.01" name="limite" placeholder="R$ 300,00" style="padding:15px;border-radius:12px;margin-bottom:15px;width:80%;max-width:300px;background:#161b22;color:white;border:1px solid #30363d;font-size:18px;"><br>
                <button type="submit" style="background:#238636;color:white;padding:15px 30px;border:none;border-radius:12px;font-weight:bold;cursor:pointer;width:80%;max-width:300px;">SALVAR CONFIGURAÇÃO</button>
            </form>
            <br><a href="/" style="color:#00aaff;text-decoration:none;">← Voltar ao Monitoramento</a>
        </body>
    """)

@app.route('/api/nomear', methods=['POST'])
def nomear():
    dados = request.json
    valor = str(dados.get('valor'))
    nome = dados.get('nome').upper()
    dados_app["assinaturas"][valor] = nome
    return jsonify({"status": "sucesso"})

@app.route('/api/dados')
def dados():
    potencia = random.randint(150, 3800)
    if potencia > 1500:
        hora_atual = datetime.now().strftime("%H:%M")
        nome_detectado = None
        for v_assinado, nome in dados_app["assinaturas"].items():
            if abs(int(v_assinado) - potencia) < (int(v_assinado) * 0.1):
                nome_detectado = nome
                break
        dados_app["picos"].insert(0, {"hora": hora_atual, "valor": potencia, "nome": nome_detectado})
        dados_app["picos"] = dados_app["picos"][:5]

    fatura_estimada = (potencia * 0.85)
    return jsonify({
        "potencia": potencia,
        "fatura": f"{fatura_estimada:.2f}".replace('.', ','),
        "picos": dados_app["picos"]
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
