from flask import Flask, request, jsonify
import requests
from requests.packages import urllib3
import json
import numpy as np
import skfuzzy as fuzz

class ManagerAgent:
    def __init__(self, api_url):
        self.api_url = api_url
        self.data = None

    def set_data(self, data):
        # Define os dados recebidos via POST para processamento. #
        self.data = data
        return True

    def calculate_metrics(self):
        # Calcula médias, facilidades, dificuldades, necessidade de ajuda e desempenho geral. #
        if not self.data:
            return None

        performance = self.data["dados"]
        result = {
            "facilidades": [],
            "dificuldades": [],
            "ajuda": False,
            "desempenho": "",
            "media": 0.0,
            "media_por_conteudo": {}
        }

        # Inicializa variáveis para cálculo da média geral
        total_correct = 0
        total_questions = 0

        # Define universo para taxa de acertos (0 a 100%)
        accuracy_universe = np.arange(0, 101, 1)

        # Define funções de pertinência fuzzy para facilidade
        low_ezness = fuzz.trapmf(accuracy_universe, [0, 0, 25, 60])  # Baixa (dificuldade)
        # medium_ezness = fuzz.trapmf(accuracy_universe, [45, 55, 60, 70])  # Média
        high_ezness = fuzz.trapmf(accuracy_universe, [60, 90, 100, 100])  # Alta (facilidade)

        # Calcula métricas para cada tipo de conteúdo
        for content_type in ["imagem", "video", "texto"]:
            correct = performance[content_type]["acertos"]
            incorrect = performance[content_type]["erros"]
            total = correct + incorrect

            # Evita divisão por zero
            accuracy_rate = (correct / total * 100) if total > 0 else 0.0

            # Armazena média por tipo de conteúdo
            result["media_por_conteudo"][content_type] = round(accuracy_rate, 2)

            # Calcula graus de pertinência fuzzy
            low_degree = fuzz.interp_membership(accuracy_universe, low_ezness, accuracy_rate)
            high_degree = fuzz.interp_membership(accuracy_universe, high_ezness, accuracy_rate)

            # Identifica facilidades e dificuldades com base nos graus de pertinência
            if round(high_degree, 2) >= 0.5:
                result["facilidades"].append({"tipo_conteudo": content_type, "grau_facilidade": round(high_degree, 2)})
            if round(low_degree, 2) >= 0.29:
                result["dificuldades"].append({"tipo_conteudo": content_type, "grau_dificuldade": round(low_degree, 2)})
                result["ajuda"] = True

            # Acumula para média geral
            total_correct += correct
            total_questions += total

        # Calcula média geral
        result["media"] = round((total_correct / total_questions * 100), 2) if total_questions > 0 else 0.0

        # Determina desempenho geral
        if result["media"] >= 90:
            result["desempenho"] = "Muito Avançado"
        elif result["media"] >= 80:
            result["desempenho"] = "Avançado"
        elif result["media"] >= 70:
            result["desempenho"] = "Médio"
        elif result["media"] >= 50:
            result["desempenho"] = "Baixo"
        else:
            result["desempenho"] = "Muito Baixo"

        return result

    def send_report_to_api(self, report):
        # Envia o relatório processado para a API. #
        try:
            urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning) # Ignorar warning SSL
            response = requests.post(f"{self.api_url}", json=report, verify=False)
            print(f"Sent Response:\n{json.dumps(report)}")
            response.raise_for_status()
            print("Relatório enviado com sucesso!")
            return True
        except requests.RequestException as e:
            print(f"Erro ao enviar relatório para a API: {e}")
            return False

# Configuração do servidor Flask
app = Flask(__name__)

@app.route('/gestor', methods=['POST'])
def call_manager():
    # Processa requisição POST com dados de desempenho e retorna relatório. #
    try:
        # Obtém os dados do request POST
        """ Formato:
        {
            "dados": {
                "imagem": {"acertos": 90, "erros": 10},
                "video": {"acertos": 80, "erros": 20},
                "texto": {"acertos": 75, "erros": 25}
            }
        }
        """
        data = request.get_json()
        if not data or "dados" not in data:
            return jsonify({"error": "Dados inválidos no request POST"}), 400

        # Inicializa o agente com a URL da API
        api_url = "https://api.exemplo.com"  # Substitua pela URL real da API
        agent = ManagerAgent(api_url)

        # Define os dados recebidos e processa
        if not agent.set_data(data):
            return jsonify({"error": "Falha ao definir os dados recebidos"}), 500

        # Calcula as métricas
        report = agent.calculate_metrics()
        if not report:
            return jsonify({"error": "Falha ao calcular métricas"}), 500

        # Envia o relatório para a API externa
        if not agent.send_report_to_api(report):
            return jsonify({"error": "Falha ao enviar relatório para a API externa"}), 500

        # Retorna o relatório como resposta ao cliente
        return jsonify(report), 200

    except Exception as e:
        print(f"Erro ao processar requisição: {e}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

# Executa o servidor Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
