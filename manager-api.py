from flask import Flask, request, jsonify
import requests
import json

class PerformanceManagerAgent:
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

        performance = self.data["performance"]
        result = {
            "strengths": [],
            "weaknesses": [],
            "needs_help": False,
            "overall_performance": "",
            "overall_average": 0.0,
            "averages_by_content": {}
        }

        # Inicializa variáveis para cálculo da média geral
        total_correct = 0
        total_questions = 0

        # Calcula métricas para cada tipo de conteúdo
        for content_type in ["image", "video", "text"]:
            correct = performance[content_type]["correct"]
            incorrect = performance[content_type]["incorrect"]
            total = correct + incorrect

            # Evita divisão por zero
            accuracy_rate = (correct / total * 100) if total > 0 else 0.0

            # Armazena média por tipo de conteúdo
            result["averages_by_content"][content_type] = round(accuracy_rate, 2)

            # Identifica facilidades e dificuldades
            if accuracy_rate >= 80:
                result["strengths"].append(content_type)
            elif accuracy_rate < 50:
                result["weaknesses"].append(content_type)
                result["needs_help"] = True

            # Acumula para média geral
            total_correct += correct
            total_questions += total

        # Calcula média geral
        result["overall_average"] = round((total_correct / total_questions * 100), 2) if total_questions > 0 else 0.0

        # Determina desempenho geral
        if result["overall_average"] >= 90:
            result["overall_performance"] = "Muito Avançado"
        elif result["overall_average"] >= 80:
            result["overall_performance"] = "Avançado"
        elif result["overall_average"] >= 70:
            result["overall_performance"] = "Médio"
        elif result["overall_average"] >= 50:
            result["overall_performance"] = "Baixo"
        else:
            result["overall_performance"] = "Muito Baixo"

        return result

    def send_report_to_api(self, report):
        # Envia o relatório processado para a API. #
        try:
            response = requests.post(f"{self.api_url}", json=report)
            response.raise_for_status()
            print("Relatório enviado com sucesso!")
            return True
        except requests.RequestException as e:
            print(f"Erro ao enviar relatório para a API: {e}")
            return False

# Configuração do servidor Flask
app = Flask(__name__)

@app.route('/process_performance', methods=['POST'])
def process_performance():
    # Processa requisição POST com dados de desempenho e retorna relatório. #
    try:
        # Obtém os dados do request POST
        data = request.get_json()
        if not data or "performance" not in data:
            return jsonify({"error": "Dados inválidos no request POST"}), 400

        # Inicializa o agente com a URL da API
        api_url = "https://api.exemplo.com"  # Substitua pela URL real da API
        agent = PerformanceManagerAgent(api_url)

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