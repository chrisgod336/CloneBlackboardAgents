from flask import Flask, request, jsonify
import requests
from requests.packages import urllib3
import json
import numpy as np
import skfuzzy as fuzz
from flask_cors import CORS

#pip install flask requests numpy scikit-fuzzy
#pip install scipy
#pip install packaging
#pip install flask-cors

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
        avalia a preferencia de conteudo com base nas taxas de acerto usando logica fuzzy.
        prioriza os tipos de conteudo em que o aluno tem melhor desempenho.
        
        args:
            taxas_acerto: dicionario com taxas de acerto por metodo
            
        returns:
            dict: dicionario com graus de preferencia para cada tipo de conteudo
        """
        # verificar se o aluno tem historico
        tem_historico = sum(taxas_acerto.values()) > 0
        
        # se nao tem historico, retornar distribuicao equilibrada
        if not tem_historico:
            return {"texto": 0.33, "imagem": 0.33, "video": 0.33}
        
        # criar universo para taxas de acerto (0 a 1)
        taxa_universe = np.linspace(0, 1, 100)
        
        # definir funcoes de pertinencia fuzzy
        baixo = fuzz.trapmf(taxa_universe, [0, 0, 0.3, 0.5])
        medio = fuzz.trimf(taxa_universe, [0.3, 0.5, 0.7])
        alto = fuzz.trapmf(taxa_universe, [0.5, 0.7, 1.0, 1.0])
        
        # calcular graus de pertinencia para cada tipo de conteudo
        graus_pertinencia = {}
        for tipo, taxa in taxas_acerto.items():
            # calcular pertinencia para cada conjunto fuzzy
            grau_baixo = fuzz.interp_membership(taxa_universe, baixo, taxa)
            grau_medio = fuzz.interp_membership(taxa_universe, medio, taxa)
            grau_alto = fuzz.interp_membership(taxa_universe, alto, taxa)
            
            # calcular preferencia baseada nos graus de pertinencia
            # quanto MAIOR a taxa de acerto, maior a preferencia (priorizar o que o aluno é bom)
            preferencia = (0.0 * grau_baixo + 0.5 * grau_medio + 1.0 * grau_alto)
            
            # se a taxa for zero (nunca acertou), dar baixa preferencia
            if taxa == 0:
                preferencia = 0.0
            
            graus_pertinencia[tipo] = preferencia
        
        # normalizar os graus para somarem 1
        soma = sum(graus_pertinencia.values())
        if soma > 0:
            for tipo in graus_pertinencia:
                graus_pertinencia[tipo] /= soma
        else:
            # se todas as taxas forem zero, distribuir igualmente
            for tipo in graus_pertinencia:
                graus_pertinencia[tipo] = 1.0 / len(graus_pertinencia)
        
        return graus_pertinencia

    def distribuir_partes(self, preferencias_fuzzy, taxas_acerto, total_partes=3):
        """
        distribui as partes de conteudo com base nas preferencias fuzzy.
        prioriza os tipos de conteudo em que o aluno tem melhor desempenho.
        
        args:
            preferencias_fuzzy: dicionario com graus de preferencia para cada tipo de conteudo
            taxas_acerto: dicionario com taxas de acerto por metodo
            total_partes: numero total de partes a distribuir
            
        returns:
            list: lista com os metodos para cada parte
        """
        # verificar se o aluno tem historico
        tem_historico = sum(taxas_acerto.values()) > 0
        
        # se nao tem historico, retornar um de cada tipo
        if not tem_historico:
            # garantir que temos pelo menos um de cada tipo
            if total_partes >= 3:
                return ["texto", "imagem", "video"]
            elif total_partes == 2:
                return ["texto", "imagem"]
            else:
                return ["texto"]
        
        # ordenar metodos por preferencia fuzzy (maior preferencia primeiro)
        metodos_ordenados = sorted(preferencias_fuzzy.keys(), 
                                 key=lambda m: preferencias_fuzzy[m], 
                                 reverse=True)
        
        # inicializar lista de partes
        partes = []
        
        # verificar se algum método tem preferência zero (nunca acertou)
        metodos_com_preferencia = [m for m in metodos_ordenados if preferencias_fuzzy[m] > 0]
        
        # se não houver métodos com preferência, usar distribuição padrão
        if not metodos_com_preferencia:
            if total_partes >= 3:
                return ["texto", "imagem", "video"]
            elif total_partes == 2:
                return ["texto", "imagem"]
            else:
                return ["texto"]
        
        # filtrar apenas métodos com preferência > 0
        metodos_ordenados = metodos_com_preferencia
        
        # distribuir partes com base nas preferências
        # se só tiver um método com preferência, todas as partes serão desse método
        if len(metodos_ordenados) == 1:
            metodo_unico = metodos_ordenados[0]
            return [metodo_unico] * total_partes
        
        # calcular quantas partes cada método deve receber com base na preferência
        total_preferencia = sum(preferencias_fuzzy[m] for m in metodos_ordenados)
        partes_por_metodo = {}
        partes_restantes = total_partes
        
        for metodo in metodos_ordenados[:-1]:  # processar todos exceto o último
            if total_preferencia > 0:
                num_partes = round(preferencias_fuzzy[metodo] / total_preferencia * total_partes)
                num_partes = min(num_partes, partes_restantes)  # não exceder o total de partes
            else:
                num_partes = 0
            
            partes_por_metodo[metodo] = num_partes
            partes_restantes -= num_partes
        
        # o último método recebe as partes restantes
        partes_por_metodo[metodos_ordenados[-1]] = partes_restantes
        
        # montar a lista final de partes
        for metodo, num_partes in partes_por_metodo.items():
            partes.extend([metodo] * num_partes)
        
        return partes

    def calculate_metrics(self): # Processa os dados do aluno e retorna as partes de conteúdo em formato JSON.
        
        if not self.data:
            return None

        try:
            # carregar dados
            dados = self.data

            # calcular taxas de acerto
            taxas_acerto = self.calcular_taxas_acerto(dados)

            # avaliar preferencia de conteudo usando a logica fuzzy real
            preferencias_fuzzy = self.avaliar_preferencia_conteudo(taxas_acerto)
            
            # distribuir partes com base nas preferencias fuzzy
            partes = self.distribuir_partes(preferencias_fuzzy, taxas_acerto)

            # criar dicionario com partes numeradas
            partes_numeradas = {}
            for i, parte in enumerate(partes, 1):
                partes_numeradas[f"parte{i}"] = parte
            
            # adicionar informacoes de diagnostico para depuracao
            diagnostico = {
                "taxas_acerto": taxas_acerto,
                "preferencias_fuzzy": preferencias_fuzzy
            }
            
            return {
                "partes": partes_numeradas,
                "diagnostico": diagnostico
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
CORS(app, resources={r"/*": {"origins": "*"}}) 

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
            return jsonify({"error": f"Falha ao calcular métricas: {report['erro']}"}), 500

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
            return jsonify({"error": f"Falha ao calcular métricas: {report['erro']}"}), 500

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
