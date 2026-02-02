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

# --- CONFIGURAÇÃO DO PWA (ÍCONE E IDENTIDADE) ---
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
                # Ícone de alta qualidade para o celular
                "src": "https://cdn-icons-png.flaticon.com/512/2731/2731636.png", 
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    })

@app.route('/sw.js')
def sw():
    response = make_response("self.addEventListener('fetch', function(event) {});")
    response.headers['Content-Type'] = 'application/javascript'
    return response

# --- DASHBOARD COM A LOGO MB OFICIAL ---
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
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: white; margin: 0; padding: 15px; }
        .container { max-width: 500px; margin: auto; }
        
        /* LOGO MB OFICIAL: CÍRCULO + RAIO + LETRAS */
        .logo-box { text-align: center; padding: 15px 0; }
        .circle-logo {
            width: 120px; height: 120px; border: 4px solid var(--accent);
            border-radius: 50%; margin: 0 auto; display: flex;
            align-items: center; justify-content: center; position: relative;
            background: rgba(0, 170, 255, 0.05); box-shadow: 0 0 20px rgba(0, 170, 255, 0.2);
        }
        .raio-svg { width: 50px; position: absolute; filter: drop-shadow(0 0 5px #00aaff); z-index: 1; }
        .letras-mb { font-size: 38px; font-weight: 900; color: white; z-index: 2; margin-left: 10px; font-family: 'Arial Black', sans-serif; }
        
        .card { background: var(--card); padding: 20px; border-radius: 18px; margin-bottom: 15px; border: 1px solid #30363d; }
        .watts { font-size: 45px; color: var(--accent); font-weight: bold; }
        .label { font-size: 11px; color: #8b949e; text-transform: uppercase; font-weight: bold; }
        .btn-config { background: var(--accent); color: white; padding: 18px; border-radius: 12px; text-decoration: none; display: block; text-align: center; font-weight: bold; }
        .alerta-box { background: rgba(218, 54, 51, 0.2); border: 1px solid var(--danger); color: #ff7b72; padding: 12px; border-radius: 8px; display: none; margin-bottom: 15px; text-align: center; font-weight: bold; }
        .pico-item { font-size: 13px; border-bottom: 1px solid #30363d; padding: 12px 0; display: flex; justify-content: space-between; align-items: center; }
        .tag-aparelho { background: rgba(0, 170, 255, 0.1); color: var(--accent); padding: 4px 8px; border-radius: 5px; font-weight: bold; border: 1px solid var(--accent); }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-box">
            <div class="circle-logo">
                <svg class="raio-svg" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
                    <path d="M18 2 L6 18 L14 18 L10 30 L26 10 L16 10 L20 2 Z" fill="#00aaff" />
                </svg>
                <span class="letras-mb">MB</span>
            </div>
            <p style="margin-top: 10px; font-size: 13px; color: #8b949e; letter-spacing: 5px; font-weight: bold;">CIRCUITO DIGITAL</p>
        </div>

        <div id="alerta_ui" class="alerta-box">⚠️ ALERTA: META ATINGIDA</div>

        <div class="card" style="text-align: center;">
            <p class="label">Potência Real</p>
            <div class="watts" id="potencia">0 W</div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div class="card">
                <p class="label">Fatura Estimada</p>
                <div style="font-size: 24px; font-weight: bold; color: var(--success);" id="fatura">R$ 0,00</div>
            </div>
            <div class="card">
                <p class="label">Sua Meta</p>
                <div style="font-size: 24px; font-weight: bold; color: #c9d1d9;">R$ {{ "%.2f"|format(limite_atual) }}</div>
            </div>
        </div>

        <div class="card"><canvas id="graficoEnergia"></canvas></div>

        <div class="card">
            <p class="label">Identificação de Aparelhos</p>
            <div id="lista_picos"></div>
        </div>

        <a href="/configurar" class="btn-config">⚙️ CONFIGURAÇÕES</a>
    </div>

    <script>
        if ('serviceWorker' in navigator) { navigator.serviceWorker.register('/sw.js'); }

        let meta = {{ limite_atual }};
        const ctx = document.getElementById('graficoEnergia').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'W', data: [], borderColor: '#00aaff', tension: 0.4, fill: true, backgroundColor: 'rgba(0, 170, 255, 0.05)' }] },
            options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#1f242c' } }, x: { display: false } } }
        });

        function identificar(valor) {
            let nome = prompt("Nomear carga de " + valor + "W:");
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
                    const vNum = parseFloat(data.fatura.replace(',','.'));
                    document.getElementById('alerta_ui').style.display = vNum > meta ? 'block' : 'none';

                    if (chart.data.labels.length > 15) { chart.data.labels.shift(); chart.data.datasets[0].data.shift(); }
                    chart.data.labels.push(new Date().toLocaleTimeString());
                    chart.data.datasets[0].data.push(data.potencia);
                    chart.update();

                    let html = '';
                    data.picos.forEach(p => {
                        let t = p.nome ? `<span class="tag-aparelho">${p.nome}</span>` : `<button onclick="identificar(${p.valor})" style="background:transparent; border:1px solid #00aaff; color:#00aaff; border-radius:5px; font-size:10px; cursor:pointer;">IDENTIFICAR</button>`;
                        html += `<div class="pico-item"><span>${p.hora} • <strong>${p.valor}W</strong></span>${t}</div>`;
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
            <h2 style="color:#00aaff">Meta Mensal</h2>
            <form method="POST">
                <input type="number" step="0.01" name="limite" style="padding:15px;border-radius:12px;margin-bottom:20px;width:80%;max-width:300px;background:#161b22;color:white;border:1px solid #30363d;"><br>
                <button type="submit" style="background:#238636;color:white;padding:15px 30px;border:none;border-radius:12px;font-weight:bold;">SALVAR</button>
            </form>
            <br><a href="/" style="color:#00aaff;text-decoration:none;">← Voltar</a>
        </body>
    """)

@app.route('/api/nomear', methods=['POST'])
def nomear():
    dados = request.json
    dados_app["assinaturas"][str(dados.get('valor'))] = dados.get('nome').upper()
    return jsonify({"status": "sucesso"})

@app.route('/api/dados')
def dados():
    pot = random.randint(150, 4000)
    nome = None
    if pot > 1500:
        for v, n in dados_app["assinaturas"].items():
            if abs(int(v) - pot) < (int(v) * 0.15):
                nome = n
                break
        dados_app["picos"].insert(0, {"hora": datetime.now().strftime("%H:%M"), "valor": pot, "nome": nome})
        dados_app["picos"] = dados_app["picos"][:5]
    fat = (pot * 0.85)
    return jsonify({"potencia": pot, "fatura": f"{fat:.2f}".replace('.', ','), "picos": dados_app["picos"]})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
            
