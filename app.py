import os
from flask import Flask, render_template_string, jsonify, request, redirect, url_for
import random
from datetime import datetime

app = Flask(__name__)

# Banco de dados temporário
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
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: white; margin: 0; padding: 15px; }
        .container { max-width: 500px; margin: auto; }
        .card { background: var(--card); padding: 20px; border-radius: 16px; margin-bottom: 15px; border: 1px solid #30363d; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        h1 { font-size: 20px; color: var(--accent); margin: 0 0 15px 0; text-align: center; }
        .valor-principal { font-size: 36px; font-weight: 800; color: var(--success); }
        .watts { font-size: 28px; color: var(--accent); font-weight: bold; }
        .label { font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
        .btn { background: var(--accent); color: white; padding: 15px; border-radius: 10px; text-decoration: none; display: block; text-align: center; font-weight: bold; margin-top: 10px; }
        .alerta { background: rgba(218, 54, 51, 0.1); border: 1px solid var(--danger); color: var(--danger); padding: 10px; border-radius: 8px; display: none; margin-bottom: 15px; font-size: 14px; text-align: center; }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .pico-item { font-size: 12px; border-bottom: 1px solid #30363d; padding: 5px 0; display: flex; justify-content: space-between; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card" style="text-align: center;">
            <h1>⚡ MB ENERGY</h1>
            <div id="alerta_container" class="alerta">⚠️ META DE GASTO ATINGIDA!</div>
            <p class="label">Consumo em Tempo Real</p>
            <div class="watts" id="potencia">0 W</div>
        </div>

        <div class="stats-grid">
            <div class="card">
                <p class="label">Previsão Mensal</p>
                <div class="valor-principal" id="fatura">R$ 0,00</div>
            </div>
            <div class="card">
                <p class="label">Sua Meta</p>
                <div class="valor-principal" style="color: #c9d1d9;">R$ {{ "%.2f"|format(limite_atual) }}</div>
            </div>
        </div>

        <div class="card">
            <canvas id="graficoConsumo"></canvas>
        </div>

        <div class="card">
            <p class="label">Últimos Picos de Consumo</p>
            <div id="lista_picos"></div>
        </div>

        <a href="/configurar" class="btn">⚙️ AJUSTAR MINHA META</a>
        <p style="text-align: center; font-size: 10px; color: #8b949e; margin-top: 20px;">MB Circuito Digital - Inteligência Energética</p>
    </div>

    <script>
        let meta = {{ limite_atual }};
        const ctx = document.getElementById('graficoConsumo').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Watts',
                    data: [],
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
        });

        function atualizar() {
            fetch('/api/dados_energia')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('potencia').innerText = data.potencia + " W";
                    document.getElementById('fatura').innerText = "R$ " + data.fatura;
                    
                    // Alerta de Meta
                    const valorFatura = parseFloat(data.fatura.replace(',', '.'));
                    document.getElementById('alerta_container').style.display = valorFatura > meta ? 'block' : 'none';

                    // Atualiza Gráfico
                    if (chart.data.labels.length > 15) { chart.data.labels.shift(); chart.data.datasets[0].data.shift(); }
                    chart.data.labels.push(new Date().toLocaleTimeString());
                    chart.data.datasets[0].data.push(data.potencia);
                    chart.update();

                    // Atualiza Picos
                    let picosHtml = '';
                    data.picos.forEach(p => {
                        picosHtml += `<div class="pico-item"><span>${p.hora}</span> <strong>${p.valor} W</strong></div>`;
                    });
                    document.getElementById('lista_picos').innerHTML = picosHtml;
                });
        }
        setInterval(atualizar, 3000);
    </script>
</body>
</html>
"""

HTML_CONFIG = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: sans-serif; background: #0d1117; color: white; text-align: center; padding: 40px 20px; }
        input { padding: 15px; border-radius: 8px; border: 1px solid #30363d; width: 100%; max-width: 300px; background: #161b22; color: white; font-size: 18px; margin-bottom: 20px; }
        button { background: #238636; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; max-width: 300px; }
        .voltar { color: #58a6ff; text-decoration: none; display: block; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>Definir Orçamento</h1>
    <p>Quanto você deseja gastar de luz este mês?</p>
    <form method="POST">
        <input type="number" step="0.01" name="limite" placeholder="R$ 250,00" required>
        <button type="submit">SALVAR META</button>
    </form>
    <a href="/" class="voltar">← Voltar ao painel</a>
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
    return render_template_string(HTML_CONFIG)

@app.route('/api/dados_energia')
def dados_energia():
    potencia = random.randint(200, 3000)
    
    # Lógica de picos: registra se for acima de 2200W
    if potencia > 2200:
        hora_pico = datetime.now().strftime("%H:%M:%S")
        dados_app["picos"].insert(0, {"hora": hora_pico, "valor": potencia})
        dados_app["picos"] = dados_app["picos"][:5] # Mantém só os últimos 5

    fatura_estimada = (potencia * 0.85) # Simulação de cálculo
    
    return jsonify({
        "potencia": potencia,
        "fatura": f"{fatura_estimada:.2f}".replace('.', ','),
        "picos": dados_app["picos"]
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
  
