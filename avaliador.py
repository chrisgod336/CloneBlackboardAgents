import json
from typing import Dict, Any, List
import os

"""
Avaliador de Exercícios
Avalia as respostas do aluno, calcula a taxa de acerto e determina se o aluno precisa refazer a aula.
Caso necessário, utiliza o Agente Tutor para recomendar métodos de aprendizagem personalizados.

Matrícula: 2122130042
"""

def avaliar_respostas(dados_json: str) -> Dict[str, Any]:
    """
    Avalia as respostas do aluno comparando com as respostas corretas.
    
    Args:
        dados_json: String JSON com as questões, respostas corretas e respostas do aluno
        
    Returns:
        Dict[str, Any]: Resultado da avaliação
    """
    try:
        # Carregar dados
        dados = json.loads(dados_json)
        questoes = dados.get("questoes", [])
        
        if not questoes:
            return {"erro": "Nenhuma questão encontrada no JSON"}
        
        # Contadores para cada tipo de questão
        contadores = {
            "texto": {"acertos": 0, "total": 0},
            "imagem": {"acertos": 0, "total": 0},
            "video": {"acertos": 0, "total": 0}
        }
        
        # Avaliar cada questão
        resultados_questoes = []
        for i, questao in enumerate(questoes):
            tipo = questao.get("tipo", "").lower()
            resposta_correta = questao.get("resposta_correta", "")
            resposta_aluno = questao.get("resposta_aluno", "")
            
            # Verificar se o tipo é válido
            if tipo not in ["texto", "imagem", "video"]:
                return {"erro": f"Tipo de questão inválido na questão {i+1}: {tipo}"}
            
            # Verificar se acertou (comparação case-insensitive)
            acertou = resposta_correta.lower() == resposta_aluno.lower()
            
            # Atualizar contadores
            contadores[tipo]["total"] += 1
            if acertou:
                contadores[tipo]["acertos"] += 1
            
            # Adicionar resultado da questão
            resultados_questoes.append({
                "numero": i + 1,
                "tipo": tipo,
                "acertou": acertou
            })
        
        # Calcular totais gerais
        total_acertos = sum(contador["acertos"] for contador in contadores.values())
        total_questoes = sum(contador["total"] for contador in contadores.values())
        
        # Calcular taxas de acerto
        taxas_acerto = {}
        for tipo, contador in contadores.items():
            if contador["total"] > 0:
                taxas_acerto[tipo] = contador["acertos"] / contador["total"] * 100
            else:
                taxas_acerto[tipo] = 0
        
        # Calcular taxa de acerto geral
        taxa_acerto_geral = (total_acertos / total_questoes * 100) if total_questoes > 0 else 0
        
        # Determinar se precisa refazer a aula (taxa de erro > 60%)
        precisa_refazer = taxa_acerto_geral < 40
        
        # Preparar dados para o tutor, se necessário
        dados_tutor = None
        recomendacao_tutor = None
        
        if precisa_refazer:
            # Preparar dados para o tutor no formato esperado
            dados_tutor = {
                "nu_acertos_texto": contadores["texto"]["acertos"],
                "nu_erros_texto": contadores["texto"]["total"] - contadores["texto"]["acertos"],
                "nu_acertos_imagem": contadores["imagem"]["acertos"],
                "nu_erros_imagem": contadores["imagem"]["total"] - contadores["imagem"]["acertos"],
                "nu_acertos_video": contadores["video"]["acertos"],
                "nu_erros_video": contadores["video"]["total"] - contadores["video"]["acertos"]
            }
            
            # Chamar o tutor para obter recomendações
            try:
                # Verificar se o módulo do tutor existe
                if os.path.exists("agente_tutor.py"):
                    from agente_tutor import processar_dados
                    resultado_tutor = processar_dados(json.dumps(dados_tutor))
                    recomendacao_tutor = resultado_tutor.get("partes", {})
                else:
                    recomendacao_tutor = {"erro": "Arquivo do tutor 'agente_tutor.py' não encontrado"}
            except Exception as e:
                recomendacao_tutor = {"erro": f"Erro ao chamar o tutor: {str(e)}"}
                print(f"Erro ao chamar o tutor: {str(e)}")
                # Tentar importar de forma alternativa
                try:
                    import sys
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                    from agente_tutor_final import processar_dados
                    resultado_tutor = processar_dados(json.dumps(dados_tutor))
                    recomendacao_tutor = resultado_tutor.get("partes", {})
                except Exception as e2:
                    print(f"Segunda tentativa falhou: {str(e2)}")
                    pass
        
        # Montar resultado final
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
        
        # Adicionar recomendação do tutor, se necessário
        if recomendacao_tutor:
            resultado["recomendacao_tutor"] = recomendacao_tutor
        
        return resultado
    
    except Exception as e:
        return {"erro": str(e)}

def formatar_saida(resultado: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formata o resultado da avaliação para o formato de saída JSON esperado.
    
    Args:
        resultado: Resultado da avaliação
        
    Returns:
        Dict[str, Any]: Resultado formatado
    """
    if "erro" in resultado:
        return {"erro": resultado["erro"]}
    
    # Formatar saída conforme especificação
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
    
    # Adicionar partes recomendadas, se necessário refazer
    if resultado["precisa_refazer"] and "recomendacao_tutor" in resultado:
        saida["partes"] = resultado["recomendacao_tutor"]
    
    return saida

def main():
    """Função principal para demonstração."""
    print("\n" + "*" * 70)
    print("*" + " " * 68 + "*")
    print("*  AVALIADOR DE EXERCÍCIOS - MATRÍCULA: 2122130042" + " " * 20 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    
    # Exemplo de dados de entrada
    exemplo_aprovado = {
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
    
    exemplo_reprovado = {
        "questoes": [
            {"tipo": "texto", "resposta_correta": "A", "resposta_aluno": "X"},
            {"tipo": "texto", "resposta_correta": "B", "resposta_aluno": "X"},
            {"tipo": "texto", "resposta_correta": "C", "resposta_aluno": "C"},
            {"tipo": "imagem", "resposta_correta": "D", "resposta_aluno": "X"},
            {"tipo": "imagem", "resposta_correta": "E", "resposta_aluno": "X"},
            {"tipo": "video", "resposta_correta": "F", "resposta_aluno": "F"},
            {"tipo": "video", "resposta_correta": "G", "resposta_aluno": "X"},
            {"tipo": "texto", "resposta_correta": "H", "resposta_aluno": "X"},
            {"tipo": "imagem", "resposta_correta": "I", "resposta_aluno": "I"},
            {"tipo": "video", "resposta_correta": "J", "resposta_aluno": "X"}
        ]
    }
    
    # Testar com exemplo de aluno aprovado
    print("\n" + "=" * 70)
    print("EXEMPLO: ALUNO APROVADO")
    print("=" * 70)
    
    resultado_aprovado = avaliar_respostas(json.dumps(exemplo_aprovado))
    saida_aprovado = formatar_saida(resultado_aprovado)
    
    print("\nDADOS DE ENTRADA:")
    print("-" * 50)
    print(f"Total de questões: {resultado_aprovado['total_questoes']['total']}")
    print(f"Questões de texto: {resultado_aprovado['total_questoes']['texto']}")
    print(f"Questões de imagem: {resultado_aprovado['total_questoes']['imagem']}")
    print(f"Questões de vídeo: {resultado_aprovado['total_questoes']['video']}")
    
    print("\nRESULTADOS:")
    print("-" * 50)
    print(f"Acertos de texto: {resultado_aprovado['acertos']['texto']}/{resultado_aprovado['total_questoes']['texto']}")
    print(f"Acertos de imagem: {resultado_aprovado['acertos']['imagem']}/{resultado_aprovado['total_questoes']['imagem']}")
    print(f"Acertos de vídeo: {resultado_aprovado['acertos']['video']}/{resultado_aprovado['total_questoes']['video']}")
    print(f"Taxa de acerto geral: {resultado_aprovado['taxa_acerto_geral']:.1f}%")
    print(f"Aprovado: {'Sim' if not resultado_aprovado['precisa_refazer'] else 'Não'}")
    
    print("\nSAÍDA JSON:")
    print("-" * 50)
    print(json.dumps(saida_aprovado, indent=2))
    
    # Salvar resultado em arquivo JSON
    with open("resultado_aluno_aprovado.json", "w", encoding="utf-8") as f:
        json.dump(saida_aprovado, f, indent=2)
    
    print(f"\nResultado JSON salvo em: resultado_aluno_aprovado.json")
    
    # Testar com exemplo de aluno reprovado
    print("\n" + "=" * 70)
    print("EXEMPLO: ALUNO REPROVADO")
    print("=" * 70)
    
    resultado_reprovado = avaliar_respostas(json.dumps(exemplo_reprovado))
    saida_reprovado = formatar_saida(resultado_reprovado)
    
    print("\nDADOS DE ENTRADA:")
    print("-" * 50)
    print(f"Total de questões: {resultado_reprovado['total_questoes']['total']}")
    print(f"Questões de texto: {resultado_reprovado['total_questoes']['texto']}")
    print(f"Questões de imagem: {resultado_reprovado['total_questoes']['imagem']}")
    print(f"Questões de vídeo: {resultado_reprovado['total_questoes']['video']}")
    
    print("\nRESULTADOS:")
    print("-" * 50)
    print(f"Acertos de texto: {resultado_reprovado['acertos']['texto']}/{resultado_reprovado['total_questoes']['texto']}")
    print(f"Acertos de imagem: {resultado_reprovado['acertos']['imagem']}/{resultado_reprovado['total_questoes']['imagem']}")
    print(f"Acertos de vídeo: {resultado_reprovado['acertos']['video']}/{resultado_reprovado['total_questoes']['video']}")
    print(f"Taxa de acerto geral: {resultado_reprovado['taxa_acerto_geral']:.1f}%")
    print(f"Aprovado: {'Sim' if not resultado_reprovado['precisa_refazer'] else 'Não'}")
    
    print("\nSAÍDA JSON:")
    print("-" * 50)
    print(json.dumps(saida_reprovado, indent=2))
    
    # Salvar resultado em arquivo JSON
    with open("resultado_aluno_reprovado.json", "w", encoding="utf-8") as f:
        json.dump(saida_reprovado, f, indent=2)
    
    print(f"\nResultado JSON salvo em: resultado_aluno_reprovado.json")
    
    print("\n" + "*" * 70)
    print("*" + " " * 68 + "*")
    print("*  EXECUÇÃO CONCLUÍDA COM SUCESSO!" + " " * 35 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)

if __name__ == "__main__":
    main()
