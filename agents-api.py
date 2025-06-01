from flask import Flask, request, jsonify
import requests
from requests.packages import urllib3
import json
import numpy as np
import skfuzzy as fuzz


############## Tutor ##############
class TutorAgent:
    """
    agente tutor simplificado
    utiliza logica fuzzy para determinar qual metodo de aprendizagem o aluno tem mais facilidade
    e retorna as partes de conteudo em formato JSON.

    Matrícula: 2122130042
  
    este codigo implementa uma simplificacao da logica fuzzy.
    as regras implementadas sao:
    1. se taxa de acerto em video e alta e as demais sao baixas, entao preferencia e video
    2. se taxa de acerto em texto e alta e as demais sao baixas, entao preferencia e texto
    3. se taxa de acerto em imagem e alta e as demais sao baixas, entao preferencia e imagem
    4. se todas as taxas de acerto sao baixas, entao preferencia e texto
    5. se todas as taxas de acerto sao altas, entao preferencia e texto

    em vez de usar bibliotecas fuzzy complexas, implementamos diretamente as regras
    com condicoes simples baseadas em limites de taxas de acerto.
    """

    def __init__(self):
        self.data = None

    def set_data(self, data):
        # Define os dados recebidos via POST para processamento. #
        self.data = data
        return True

    def calcular_taxas_acerto(self, dados):
        """
        Calcula as taxas de acerto para cada método de aprendizagem.
        """
        
        taxas = {
            "texto": 0,
            "imagem": 0,
            "video": 0
        }

        # Calcular taxa de acerto para texto
        acertos_texto = dados["nu_acertos_texto"]
        erros_texto = dados["nu_erros_texto"]
        total_texto = acertos_texto + erros_texto
        if total_texto > 0:
            taxas["texto"] = acertos_texto / total_texto
        
        # Calcular taxa de acerto para imagem
        acertos_imagem = dados["nu_acertos_imagem"]
        erros_imagem = dados["nu_erros_imagem"]
        total_imagem = acertos_imagem + erros_imagem
        if total_imagem > 0:
            taxas["imagem"] = acertos_imagem / total_imagem
        
        # Calcular taxa de acerto para vídeo
        acertos_video = dados["nu_acertos_video"]
        erros_video = dados["nu_erros_video"]
        total_video = acertos_video + erros_video
        if total_video > 0:
            taxas["video"] = acertos_video / total_video
        
        return taxas

    def avaliar_preferencia_conteudo(self, taxas_acerto):
        """
        avalia a preferencia de conteudo com base nas taxas de acerto.
        simplificacao da logica fuzzy para determinar a preferencia.
        
        args:
            taxas_acerto: dicionario com taxas de acerto por metodo
            
        returns:
            str: metodo preferido (texto, imagem ou video)
        """
        # definir limites para considerar uma taxa como alta ou baixa
        limite_alto = 0.6  # 60% de acerto ou mais e considerado alto
        limite_baixo = 0.4  # menos de 40% de acerto e considerado baixo
        
        # verificar regra 1: se video e alto e os demais sao baixos, entao preferencia e video
        if (taxas_acerto["video"] >= limite_alto and 
            taxas_acerto["texto"] <= limite_baixo and 
            taxas_acerto["imagem"] <= limite_baixo):
            return "video"
        
        # verificar regra 2: se texto e alto e os demais sao baixos, entao preferencia e texto
        elif (taxas_acerto["texto"] >= limite_alto and 
            taxas_acerto["video"] <= limite_baixo and 
            taxas_acerto["imagem"] <= limite_baixo):
            return "texto"
        
        # verificar regra 3: se imagem e alto e os demais sao baixos, entao preferencia e imagem
        elif (taxas_acerto["imagem"] >= limite_alto and 
            taxas_acerto["texto"] <= limite_baixo and 
            taxas_acerto["video"] <= limite_baixo):
            return "imagem"
        
        # verificar regra 4: se todos sao baixos, entao preferencia e texto
        elif (taxas_acerto["texto"] <= limite_baixo and 
            taxas_acerto["imagem"] <= limite_baixo and 
            taxas_acerto["video"] <= limite_baixo):
            return "texto"
        
        # verificar regra 5: se todos sao altos, entao preferencia e texto
        elif (taxas_acerto["texto"] >= limite_alto and 
            taxas_acerto["imagem"] >= limite_alto and 
            taxas_acerto["video"] >= limite_alto):
            return "texto"
        
        # caso padrao: retornar o metodo com maior taxa de acerto
        else:
            return max(taxas_acerto.items(), key=lambda x: x[1])[0]

    def distribuir_partes(self, preferencia, taxas_acerto, total_partes=3):
        """
        distribui as partes de conteudo com base na preferencia e taxas de acerto.
        
        args:
            preferencia: metodo preferido (texto, imagem ou video)
            taxas_acerto: dicionario com taxas de acerto por metodo
            total_partes: numero total de partes a distribuir
            
        returns:
            list: lista com os metodos para cada parte
        """
        # ordenar metodos por taxa de acerto
        metodos_ordenados = sorted(taxas_acerto.keys(), key=lambda m: taxas_acerto[m], reverse=True)
        
        # inicializar lista de partes
        partes = []
        
        # garantir que o metodo preferido receba pelo menos uma parte
        partes.append(preferencia)
        
        # distribuir o restante das partes
        partes_restantes = total_partes - 1
        
        # metodo preferido recebe mais uma parte
        if partes_restantes > 0:
            partes.append(preferencia)
            partes_restantes -= 1
        
        # se ainda houver partes, o segundo metodo com maior taxa recebe uma parte
        if partes_restantes > 0:
            segundo_metodo = metodos_ordenados[1] if metodos_ordenados[0] == preferencia else metodos_ordenados[0]
            partes.append(segundo_metodo)
        
        return partes

    def calculate_metrics(self): # Processa os dados do aluno e retorna as partes de conteúdo em formato JSON.
        
        if not self.data:
            return None

        try:
            # carregar dados
            dados = self.data

            # calcular taxas de acerto
            taxas_acerto = self.calcular_taxas_acerto(dados)

            # avaliar preferencia de conteudo usando a logica fuzzy simplificada
            preferencia = self.avaliar_preferencia_conteudo(taxas_acerto)
            
            # distribuir partes
            partes = self.distribuir_partes(preferencia, taxas_acerto)

            # criar dicionario com partes numeradas
            partes_numeradas = {}
            for i, parte in enumerate(partes, 1):
                partes_numeradas[f"parte{i}"] = parte
            
            return {
                "partes": partes_numeradas
            }
        except Exception as e:
            return {"erro": str(e)}


############## Avaliador ##############
class EvaluatorAgent:
    """
    avaliador de exercicios
    avalia as respostas do aluno, calcula a taxa de acerto e determina se o aluno precisa refazer a aula.
    caso necessario, utiliza o agente tutor para recomendar metodos de aprendizagem personalizados.

    matricula: 2122130042
    """

    def __init__(self):
        self.data = None

    def set_data(self, data):
        # Define os dados recebidos via POST para processamento. #
        self.data = data
        return True

    def calculate_metrics(self): # Avalia as respostas do aluno comparando com as respostas corretas.
        if not self.data:
            return None

        # carregar dados
        questoes = self.data["questoes"]            
        if not questoes:
            return {"erro": "nenhuma questao encontrada no json"}
        
        # contadores para cada tipo de questao
        contadores = {
            "texto": {"acertos": 0, "total": 0},
            "imagem": {"acertos": 0, "total": 0},
            "video": {"acertos": 0, "total": 0}
        }
        
        # avaliar cada questao
        resultados_questoes = []
        for i, questao in enumerate(questoes):
            tipo = questao.get("tipo", "").lower()
            resposta_correta = questao.get("resposta_correta", "")
            resposta_aluno = questao.get("resposta_aluno", "")
            
            # verificar se o tipo e valido
            if tipo not in ["texto", "imagem", "video"]:
                return {"erro": f"tipo de questao invalido na questao {i+1}: {tipo}"}
            
            # verificar se acertou (comparacao case-insensitive)
            acertou = resposta_correta.lower() == resposta_aluno.lower()
            
            # atualizar contadores
            contadores[tipo]["total"] += 1
            if acertou:
                contadores[tipo]["acertos"] += 1
            
            # adicionar resultado da questao
            resultados_questoes.append({
                "numero": i + 1,
                "tipo": tipo,
                "acertou": acertou
            })
        
        # calcular totais gerais
        total_acertos = sum(contador["acertos"] for contador in contadores.values())
        total_questoes = sum(contador["total"] for contador in contadores.values())
        
        # calcular taxas de acerto
        taxas_acerto = {}
        for tipo, contador in contadores.items():
            if contador["total"] > 0:
                taxas_acerto[tipo] = contador["acertos"] / contador["total"] * 100
            else:
                taxas_acerto[tipo] = 0
        
        # calcular taxa de acerto geral
        taxa_acerto_geral = (total_acertos / total_questoes * 100) if total_questoes > 0 else 0
        
        # determinar se precisa refazer a aula (taxa de acerto < 70%)
        precisa_refazer = taxa_acerto_geral < 70
        
        # preparar dados para o tutor, se necessario
        dados_tutor = None
        recomendacao_tutor = None
        
        if precisa_refazer:
            # preparar dados para o tutor no formato esperado
            dados_tutor = {
                "nu_acertos_texto": contadores["texto"]["acertos"],
                "nu_erros_texto": contadores["texto"]["total"] - contadores["texto"]["acertos"],
                "nu_acertos_imagem": contadores["imagem"]["acertos"],
                "nu_erros_imagem": contadores["imagem"]["total"] - contadores["imagem"]["acertos"],
                "nu_acertos_video": contadores["video"]["acertos"],
                "nu_erros_video": contadores["video"]["total"] - contadores["video"]["acertos"]
            }
            
            # chamar o tutor para obter recomendacoes
            agente_tutor = TutorAgent()
            agente_tutor.set_data(dados_tutor)
            resultado_tutor = agente_tutor.calculate_metrics()
            recomendacao_tutor = resultado_tutor
        
        # montar resultado final
        resultado = {
            "acertos": {
                "texto": contadores["texto"]["acertos"],
                "imagem": contadores["imagem"]["acertos"],
                "video": contadores["video"]["acertos"],
                "total": total_acertos
            },
            "total_questoes": {
                "texto": contadores["texto"]["total"],
                "imagem": contadores["imagem"]["total"],
                "video": contadores["video"]["total"],
                "total": total_questoes
            },
            "taxas_acerto": taxas_acerto,
            "taxa_acerto_geral": taxa_acerto_geral,
            "precisa_refazer": precisa_refazer,
            "resultados_questoes": resultados_questoes
        }
        
        # adicionar recomendacao do tutor, se necessario
        if recomendacao_tutor:
            resultado["recomendacao_tutor"] = recomendacao_tutor
        
        if "erro" in resultado:
            saida = {"erro": resultado["erro"]}
        else:
            saida = {
                "acertos": {
                    "texto": resultado["acertos"]["texto"],
                    "imagem": resultado["acertos"]["imagem"],
                    "video": resultado["acertos"]["video"]
                },
                "erros": {
                    "texto": resultado["total_questoes"]["texto"] - resultado["acertos"]["texto"],
                    "imagem": resultado["total_questoes"]["imagem"] - resultado["acertos"]["imagem"],
                    "video": resultado["total_questoes"]["video"] - resultado["acertos"]["video"]
                },
                "nota": round(resultado["taxa_acerto_geral"], 1),
                "aprovado": not resultado["precisa_refazer"]
            }
            
            # adicionar partes recomendadas, se necessario refazer
            if resultado["precisa_refazer"] and "recomendacao_tutor" in resultado:
                saida["partes"] = resultado["recomendacao_tutor"]
        
        return saida


############## Gestor ##############
# autor: fabio melo martins | matricula: 2122130014
class ManagerAgent:
    def __init__(self):
        self.data = None

    def set_data(self, data):
        # Define os dados recebidos via POST para processamento.
        self.data = data
        return True

    def calculate_metrics(self): # calcula medias, facilidades, dificuldades, necessidade de ajuda e desempenho geral.
        if not self.data:
            return None

        performance = self.data["dados"]
        print(performance)
        result = {
            "facilidades": [],
            "dificuldades": [],
            "ajuda": False,
            "desempenho": "",
            "media": 0.0,
            "media_por_conteudo": {}
        }

        # inicializa variaveis para calculo da media geral
        total_correct = 0
        total_questions = 0

        # define universo para taxa de acertos (0 a 100%)
        accuracy_universe = np.arange(0, 101, 1)

        # define funcoes de pertinencia fuzzy para facilidade
        low_ezness = fuzz.trapmf(accuracy_universe, [0, 0, 25, 60])  # baixa (dificuldade)
        high_ezness = fuzz.trapmf(accuracy_universe, [60, 90, 100, 100])  # alta (facilidade)

        # calcula metricas para cada tipo de conteudo
        for content_type in ["imagem", "video", "texto"]:
            correct = performance[content_type]["acertos"]
            incorrect = performance[content_type]["erros"]
            total = correct + incorrect

            # evita divisao por zero
            accuracy_rate = (correct / total * 100) if total > 0 else 0.0

            # armazena media por tipo de conteudo
            result["media_por_conteudo"][content_type] = round(accuracy_rate, 2)

            # calcula graus de pertinencia fuzzy
            low_degree = fuzz.interp_membership(accuracy_universe, low_ezness, accuracy_rate)
            high_degree = fuzz.interp_membership(accuracy_universe, high_ezness, accuracy_rate)

            # identifica facilidades e dificuldades com base nos graus de pertinencia
            if round(high_degree, 2) >= 0.5:
                result["facilidades"].append({"tipo_conteudo": content_type, "grau_facilidade": round(high_degree, 2)})
            if round(low_degree, 2) >= 0.29:
                result["dificuldades"].append({"tipo_conteudo": content_type, "grau_dificuldade": round(low_degree, 2)})
                result["ajuda"] = True

            # acumula para media geral
            total_correct += correct
            total_questions += total

        # calcula media geral
        result["media"] = round((total_correct / total_questions * 100), 2) if total_questions > 0 else 0.0

        # determina desempenho geral
        if result["media"] >= 90:
            result["desempenho"] = "muito avancado"
        elif result["media"] >= 80:
            result["desempenho"] = "avancado"
        elif result["media"] >= 70:
            result["desempenho"] = "medio"
        elif result["media"] >= 50:
            result["desempenho"] = "baixo"
        else:
            result["desempenho"] = "muito baixo"

        return result


############## API que comanda o sistema multiagente ##############
# autor: fabio melo martins | matricula: 2122130014

# configuracao do servidor flask
app = Flask(__name__)


### endpoint de entrada do tutor ###
@app.route('/tutor', methods=['POST'])
def call_tutor():
    # Processa requisição POST com dados de desempenho e retorna relatório. #
    try:
        # Obtém os dados do request POST
        """ Formato:
        {
            "nu_acertos_texto": 25,
            "nu_erros_texto": 5,
            "nu_acertos_imagem": 10,
            "nu_erros_imagem": 10,
            "nu_acertos_video": 8,
            "nu_erros_video": 12
        }
        """
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados inválidos no request POST"}), 400

        # Inicializa o agente
        agent = TutorAgent()

        # Define os dados recebidos e processa
        if not agent.set_data(data):
            return jsonify({"error": "Falha ao definir os dados recebidos"}), 500

        # Calcula as métricas
        report = agent.calculate_metrics()
        if not report:
            return jsonify({"error": "Falha ao calcular métricas"}), 500
        if "erro" in report:
            return jsonify({"error": f"Falha ao calcular métricas: {report["erro"]}"}), 500

        # Retorna o relatório como resposta ao cliente
        return jsonify(report), 200

    except Exception as e:
        print(f"Erro ao processar requisição: {e}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


### endpoint de entrada do avaliador ###
@app.route('/avaliador', methods=['POST'])
def call_evaluator():
    # Processa requisição POST com dados de desempenho e retorna relatório. #
    try:
        # Obtém os dados do request POST
        """ Formato:
        {
            "questoes": [
                {"tipo": "texto", "resposta_correta": "A", "resposta_aluno": "A"},
                {"tipo": "texto", "resposta_correta": "B", "resposta_aluno": "B"},
                {"tipo": "texto", "resposta_correta": "C", "resposta_aluno": "C"},
                {"tipo": "imagem", "resposta_correta": "D", "resposta_aluno": "D"},
                {"tipo": "imagem", "resposta_correta": "E", "resposta_aluno": "E"},
                {"tipo": "video", "resposta_correta": "F", "resposta_aluno": "F"},
                {"tipo": "video", "resposta_correta": "G", "resposta_aluno": "G"},
                {"tipo": "texto", "resposta_correta": "H", "resposta_aluno": "X"},
                {"tipo": "imagem", "resposta_correta": "I", "resposta_aluno": "X"},
                {"tipo": "video", "resposta_correta": "J", "resposta_aluno": "X"}
            ]
        }
        """
        
        data = request.get_json()
        if not data or "questoes" not in data:
            return jsonify({"error": "Dados inválidos no request POST"}), 400

        # Inicializa o agente
        agent = EvaluatorAgent()

        # Define os dados recebidos e processa
        if not agent.set_data(data):
            return jsonify({"error": "Falha ao definir os dados recebidos"}), 500

        # Calcula as métricas
        report = agent.calculate_metrics()
        if not report:
            return jsonify({"error": "Falha ao calcular métricas"}), 500
        if "erro" in report:
            return jsonify({"error": f"Falha ao calcular métricas: {report["erro"]}"}), 500

        # Retorna o relatório como resposta ao cliente
        return jsonify(report), 200

    except Exception as e:
        print(f"Erro ao processar requisição: {e}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


### Endpoint de entrada do gestor ###
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

        # Inicializa o agente
        agent = ManagerAgent()

        # Define os dados recebidos e processa
        if not agent.set_data(data):
            return jsonify({"error": "Falha ao definir os dados recebidos"}), 500

        # Calcula as métricas
        report = agent.calculate_metrics()
        if not report:
            return jsonify({"error": "Falha ao calcular métricas"}), 500

        # Retorna o relatório como resposta ao cliente
        return jsonify(report), 200

    except Exception as e:
        print(f"Erro ao processar requisição: {e}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


# Executa o servidor Flask
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
