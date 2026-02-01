import os
from flask import Flask, render_template_string, jsonify, request, redirect, url_for
import random
from datetime import datetime

app = Flask(__name__)

dados_app = {
    "limite_gasto": 300.00,
    "picos": []
}

HTML_GERAL = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MB Energy Intelligence</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root { --bg: #0d1117; --card: #161b22; --accent: #58a6ff; --success: #238636; --danger: #da3633; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: white; margin: 0; padding: 15px; }
        .container { max-width: 500px; margin: auto; }
        .card { background: var(--card); padding: 20px; border-radius: 16px; margin-bottom: 15px; border: 1px solid #30363d; }
        h1 { font-size: 22px; color: var(--accent); text-align: center; margin-bottom: 20px; }
        .valor-principal { font-size: 32px; font-weight: bold; color: var(--success); }
        .watts { font-size: 28px; color: var(--accent); font-weight: bold; }
        .label { font-size: 11px; color: #8b949e; text-transform: uppercase; margin-bottom: 5px; }
        .btn { background: var(--accent); color: white; padding: 15px; border-radius: 10px; text-decoration: none; display: block; text-align: center; font-weight: bold; }
        .alerta-box { background: rgba(218, 54, 51, 0.15); border: 1px solid var(--danger); color: var(--danger); padding: 12px; border-radius: 8px; display: none; margin-bottom: 15px; text-align: center; font-weight: bold; }
        .pico-item { font-size: 13px; border-bottom: 1px solid #30363d; padding: 8px 0; display: flex; justify-content: space-between; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>⚡ MB ENERGY INTEL</h1>
            <div id="alerta_ui" class="alerta-box">⚠️ ATENÇÃO: META DE GASTO ATINGIDA!</div>
            <p class="label">Potência Atual</p>
            <div class="watts" id="potencia">0 W</div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div class="card">
                <p class="label">Previsão Fatura</p>
                <div class="valor-principal" id="fatura">R$ 0,00</div>
            </div>
            <div class="card">
                <p class="label">Sua Meta</p>
                <div class="valor-principal" style="color: #c9d1d9;">R$ {{ "%.2f"|format(limite_atual) }}</div>
            </div>
        </div>

        <div class="card">
            <canvas id="grafico"></canvas>
        </div>

        <div class="card">
            <p class="label">Histórico de Picos (>2200W)</p>
            <div id="lista_picos"></div>
        </div>

        <a href="/configurar" class="btn">⚙️ CONFIGURAR MINHA META</a>
        <p style="text-align: center; font-size: 10px; color: #484f58; margin-top: 20px;">MB Circuito Digital - Salvador/BA</p>
    </div>

    <script>
        let meta = {{ limite_atual }};
        const ctx = document.getElementById('grafico').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Watts', data: [], borderColor: '#58a6ff', tension: 0.4, fill: true, backgroundColor: 'rgba(88, 166, 255, 0.1)' }] },
            options: { plugins: { legend: { display: false } } }
        });

        function atualizar() {
            fetch('/api/dados')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('potencia').innerText = data.potencia + " W";
                    document.getElementById('fatura').innerText = "R$ " + data.fatura;
                    
                    const valorNum = parseFloat(data.fatura.replace(',','.'));
                    document.getElementById('alerta_ui').style.display = valorNum > meta ? 'block' : 'none';

                    if (chart.data.labels.length > 10) { chart.data.labels.shift(); chart.data.datasets[0].data.shift(); }
                    chart.data.labels.push(new Date().toLocaleTimeString());
                    chart.data.datasets[0].data.push(data.potencia);
                    chart.update();

                    let html = '';
                    data.picos.forEach(p => html += `<div class="pico-item"><span>${p.hora}</span><strong>${p.valor}W</strong></div>`);
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
            <h2>Definir Meta de Gasto</h2>
            <form method="POST">
                <input type="number" step="0.01" name="limite" placeholder="Ex: 200.00" style="padding:15px;border-radius:8px;margin-bottom:10px;width:80%;max-width:300px;"><br>
                <button type="submit" style="background:#238636;color:white;padding:15px 30px;border:none;border-radius:8px;font-weight:bold;">SALVAR CONFIGURAÇÃO</button>
            </form>
            <br><a href="/" style="color:#58a6ff;text-decoration:none;">← Voltar ao Dashboard</a>
        </body>
    """)

@app.route('/api/dados')
def dados():
    potencia = random.randint(150, 2800)
    if potencia > 2200:
        dados_app["picos"].insert(0, {"hora": datetime.now().strftime("%H:%M:%S"), "valor": potencia})
        dados_app["picos"] = dados_app["picos"][:5]

    valor_fatura = (potencia * 0.82)
    return jsonify({
        "potencia": potencia,
        "fatura": f"{valor_fatura:.2f}".replace('.', ','),
        "picos": dados_app["picos"]
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
