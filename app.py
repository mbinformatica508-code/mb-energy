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
                # Este link aponta para um ícone de raio azul profissional para a tela inicial
                "src": "https://img.icons8.com/external-flat-icons-inmotus-design/512/external-Energy-energy-flat-icons-inmotus-design-12.png",
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

# --- DASHBOARD COM A LOGO MB ---
HTML_GERAL = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="manifest" href="/manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>MB Energy Intelligence</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root { --bg: #0d1117; --card: #161b22; --accent: #00aaff; --success: #238636; --danger: #da3633; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: white; margin: 0; padding: 15px; }
        .container { max-width: 500px; margin: auto; }
        
        /* LOGO MB COM RAIO */
        .header-logo { text-align: center; padding: 20px 0; }
        .logo-svg { width: 130px; filter: drop-shadow(0 0 8px rgba(0, 170, 255, 0.4)); }
        
        .card { background: var(--card); padding: 20px; border-radius: 18px; margin-bottom: 15px; border: 1px solid #30363d; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        .label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; font-weight: bold; }
        .watts { font-size: 48px; color: var(--accent); font-weight: 800; margin: 5px 0; }
        .valor-fatura { font-size: 30px; font-weight: bold; color: var(--success); }
        .btn-config { background: var(--accent); color: white; padding: 18px; border-radius: 12px; text-decoration: none; display: block; text-align: center; font-weight: bold; margin-top: 10px; }
        .alerta-box { background: rgba(218, 54, 51, 0.15); border: 1px solid var(--danger); color: #ff7b72; padding: 15px; border-radius: 10px; display: none; margin-bottom: 15px; text-align: center; font-weight: bold; }
        .pico-item { font-size: 14px; border-bottom: 1px solid #30363d; padding: 12px 0; display: flex; justify-content: space-between; align-items: center; }
        .btn-iden { background: transparent; border: 1px solid var(--accent); color: var(--accent); padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: bold; cursor: pointer; }
        .tag-aparelho { background: rgba(0, 170, 255, 0.1); color: var(--accent); padding: 4px 10px; border-radius: 6px; font-weight: bold; border: 1px solid var(--accent); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header-logo">
            <svg class="logo-svg" viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg">
                <path d="M40 10 L25 45 L45 45 L30 75 L70 35 L50 35 L65 10 Z" fill="#00aaff" />
                <text x="80" y="55" font-family="Arial Black" font-size="52" fill="white">MB</text>
            </svg>
            <p style="margin-top: -5px; font-size: 12px; color: #8b949e; letter-spacing: 4px;">CIRCUITO DIGITAL</p>
        </div>

        <div id="alerta_ui" class="alerta-box">⚠️ LIMITE DE GASTO ATINGIDO</div>

        <div class="card" style="text-align: center;">
            <p class="label">Potência em Tempo Real</p>
            <div class="watts" id="potencia">0 W</div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div class="card">
                <p class="label">Fatura Estimada</p>
                <div class="valor-fatura" id="fatura">R$ 0,00</div>
            </div>
            <div class="card">
                <p class="label">Sua Meta</p>
                <div class="valor-fatura" style="color: #c9d1d9;">R$ {{ "%.2f"|format(limite_atual) }}</div>
            </div>
        </div>

        <div class="card">
            <canvas id="graficoEnergia"></canvas>
        </div>

        <div class="card">
            <p class="label">Identificação Inteligente (NILM)</p>
            <div id="lista_picos" style="margin-top: 10px;"></div>
        </div>

        <a href="/configurar" class="btn-config">⚙️ AJUSTAR CONFIGURAÇÕES</a>
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
            let nome = prompt("Qual aparelho consome " + valor + "W?");
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
                    document.getElementById('alerta_ui').style.display = valorNum > meta ? 'block' : 'none';

                    if (chart.data.labels.length > 15) { chart.data.labels.shift(); chart.data.datasets[0].data.shift(); }
                    chart.data.labels.push(new Date().toLocaleTimeString());
                    chart.data.datasets[0].data.push(data.potencia);
                    chart.update();

                    let html = '';
                    data.picos.forEach(p => {
                        let tag = p.nome ? `<span class="tag-aparelho">${p.nome}</span>` : `<button class="btn-iden" onclick="identificar(${p.valor})">IDENTIFICAR</button>`;
                        html += `<div class="pico-item"><span>${p.hora} • <strong>${p.valor}W</strong></span>${tag}</div>`;
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
            <h2 style="color:#00aaff">Definir Meta Mensal</h2>
            <form method="POST">
                <input type="number" step="0.01" name="limite" style="padding:15px;border-radius:12px;margin-bottom:20px;width:80%;max-width:300px;background:#161b22;color:white;border:1px solid #30363d;"><br>
                <button type="submit" style="background:#238636;color:white;padding:15px 30px;border:none;border-radius:12px;font-weight:bold;width:80%;max-width:300px;">SALVAR META</button>
            </form>
            <br><a href="/" style="color:#00aaff;text-decoration:none;">← Voltar ao Dashboard</a>
        </body>
    """)

@app.route('/api/nomear', methods=['POST'])
def nomear():
    dados = request.json
    dados_app["assinaturas"][str(dados.get('valor'))] = dados.get('nome').upper()
    return jsonify({"status": "sucesso"})

@app.route('/api/dados')
def dados():
    potencia = random.randint(150, 4500)
    if potencia > 1500:
        nome_detectado = None
        for v_assinado, nome in dados_app["assinaturas"].items():
            if abs(int(v_assinado) - potencia) < (int(v_assinado) * 0.15):
                nome_detectado = nome
                break
        dados_app["picos"].insert(0, {"hora": datetime.now().strftime("%H:%M"), "valor": potencia, "nome": nome_detectado})
        dados_app["picos"] = dados_app["picos"][:5]

    fatura = (potencia * 0.85)
    return jsonify({"potencia": potencia, "fatura": f"{fatura:.2f}".replace('.', ','), "picos": dados_app["picos"]})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
