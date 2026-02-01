import os
from flask import Flask, render_template_string, jsonify
import random # Para simular o consumo enquanto o sensor não chega

app = Flask(__name__)

# CONFIGURAÇÃO DE CUSTO (Salvador/BA média)
PRECO_KWH = 0.92 

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MB Energy Intelligence</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0b0e14; color: white; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: auto; }
        .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #1e3c72; padding-bottom: 10px; }
        .card { background: #161b22; padding: 20px; border-radius: 15px; margin-bottom: 20px; text-align: center; border: 1px solid #30363d; }
        .valor-real { font-size: 32px; font-weight: bold; color: #238636; }
        .watts { font-size: 24px; color: #58a6ff; }
        .btn-alerta { background: #d73a49; color: white; padding: 10px; border-radius: 8px; text-decoration: none; display: inline-block; margin-top: 10px; font-size: 14px; }
        canvas { margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>MB ENERGY ⚡</h1>
            <p>Monitoramento em Tempo Real</p>
        </div>

        <div class="card">
            <p>CONSUMO AGORA</p>
            <div class="watts" id="potencia">0 W</div>
        </div>

        <div class="card">
            <p>PREVISÃO DA FATURA (MÊS)</p>
            <div class="valor-real" id="fatura">R$ 0,00</div>
            <p style="font-size: 12px; color: #8b949e;">Baseado no consumo atual</p>
        </div>

        <div class="card">
            <canvas id="graficoConsumo"></canvas>
        </div>

        <div style="text-align:center;">
            <a href="#" class="btn-alerta">CONFIGURAR LIMITE DE GASTO</a>
        </div>
    </div>

    <script>
        let ctx = document.getElementById('graficoConsumo').getContext('2d');
        let dadosGrafico = {
            labels: [],
            datasets: [{
                label: 'Watts (W)',
                data: [],
                borderColor: '#58a6ff',
                tension: 0.4,
                fill: true,
                backgroundColor: 'rgba(88, 166, 255, 0.1)'
            }]
        };

        let chart = new Chart(ctx, { type: 'line', data: dadosGrafico });

        // Função para simular a leitura do sensor
        function atualizarDados() {
            fetch('/api/dados_energia')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('potencia').innerText = data.potencia + " W";
                    document.getElementById('fatura').innerText = "R$ " + data.fatura_estimada;

                    // Atualiza Gráfico
                    let agora = new Date().toLocaleTimeString();
                    if (chart.data.labels.length > 10) {
                        chart.data.labels.shift();
                        chart.data.datasets[0].data.shift();
                    }
                    chart.data.labels.push(agora);
                    chart.data.datasets[0].data.push(data.potencia);
                    chart.update();
                });
        }

        setInterval(atualizarDados, 3000); // Atualiza a cada 3 segundos
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_DASHBOARD)

@app.route('/api/dados_energia')
def dados_energia():
    # Aqui, futuramente, pegaremos os dados REAIS do ESP32
    # Por enquanto, simulamos uma casa ligando e desligando coisas
    potencia_simulada = random.randint(300, 2500) 
    fatura_simulada = (potencia_simulada * 0.72) # Cálculo fictício para demonstração
    
    return jsonify({
        "potencia": potencia_simulada,
        "fatura_estimada": f"{fatura_simulada:.2f}".replace('.', ',')
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
  
