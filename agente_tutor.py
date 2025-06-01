import json
from typing import Dict, Any

"""
Agente Tutor Simplificado
Utiliza lógica fuzzy para determinar qual método de aprendizagem o aluno tem mais facilidade
e retorna as partes de conteúdo em formato JSON.

Matrícula: 2122130042
"""

# Comentário sobre a lógica fuzzy simplificada
"""
Este código implementa uma simplificação da lógica fuzzy.
As regras implementadas são:
1. Se taxa de acerto em vídeo é alta e as demais são baixas, então preferência é vídeo
2. Se taxa de acerto em texto é alta e as demais são baixas, então preferência é texto
3. Se taxa de acerto em imagem é alta e as demais são baixas, então preferência é imagem
4. Se todas as taxas de acerto são baixas, então preferência é texto
5. Se todas as taxas de acerto são altas, então preferência é texto

Em vez de usar bibliotecas fuzzy complexas, implementamos diretamente as regras
com condições simples baseadas em limites de taxas de acerto.
"""


def calcular_taxas_acerto(dados):
    """
    Calcula as taxas de acerto para cada método de aprendizagem.
    
    Args:
        dados: Dicionário com contadores de acertos e erros por método
        
    Returns:
        Dict[str, float]: Taxas de acerto (0-1) para cada método
    """
    taxas = {}
    
    # Calcular taxa de acerto para texto
    acertos_texto = dados.get("nu_acertos_texto", 0)
    erros_texto = dados.get("nu_erros_texto", 0)
    total_texto = acertos_texto + erros_texto
    taxas["texto"] = acertos_texto / total_texto if total_texto > 0 else 0
    
    # Calcular taxa de acerto para imagem
    acertos_imagem = dados.get("nu_acertos_imagem", 0)
    erros_imagem = dados.get("nu_erros_imagem", 0)
    total_imagem = acertos_imagem + erros_imagem
    taxas["imagem"] = acertos_imagem / total_imagem if total_imagem > 0 else 0
    
    # Calcular taxa de acerto para vídeo
    acertos_video = dados.get("nu_acertos_video", 0)
    erros_video = dados.get("nu_erros_video", 0)
    total_video = acertos_video + erros_video
    taxas["video"] = acertos_video / total_video if total_video > 0 else 0
    
    return taxas


def avaliar_preferencia_conteudo(taxas_acerto):
    """
    Avalia a preferência de conteúdo com base nas taxas de acerto.
    Simplificação da lógica fuzzy para determinar a preferência.
    
    Args:
        taxas_acerto: Dicionário com taxas de acerto por método
        
    Returns:
        str: Método preferido (texto, imagem ou video)
    """
    # Definir limites para considerar uma taxa como alta ou baixa
    limite_alto = 0.6  # 60% de acerto ou mais é considerado alto
    limite_baixo = 0.4  # Menos de 40% de acerto é considerado baixo
    
    # Verificar regra 1: Se vídeo é alto e os demais são baixos, então preferência é vídeo
    if (taxas_acerto["video"] >= limite_alto and 
        taxas_acerto["texto"] <= limite_baixo and 
        taxas_acerto["imagem"] <= limite_baixo):
        return "video"
    
    # Verificar regra 2: Se texto é alto e os demais são baixos, então preferência é texto
    elif (taxas_acerto["texto"] >= limite_alto and 
          taxas_acerto["video"] <= limite_baixo and 
          taxas_acerto["imagem"] <= limite_baixo):
        return "texto"
    
    # Verificar regra 3: Se imagem é alto e os demais são baixos, então preferência é imagem
    elif (taxas_acerto["imagem"] >= limite_alto and 
          taxas_acerto["texto"] <= limite_baixo and 
          taxas_acerto["video"] <= limite_baixo):
        return "imagem"
    
    # Verificar regra 4: Se todos são baixos, então preferência é texto
    elif (taxas_acerto["texto"] <= limite_baixo and 
          taxas_acerto["imagem"] <= limite_baixo and 
          taxas_acerto["video"] <= limite_baixo):
        return "texto"
    
    # Verificar regra 5: Se todos são altos, então preferência é texto
    elif (taxas_acerto["texto"] >= limite_alto and 
          taxas_acerto["imagem"] >= limite_alto and 
          taxas_acerto["video"] >= limite_alto):
        return "texto"
    
    # Caso padrão: retornar o método com maior taxa de acerto
    else:
        return max(taxas_acerto.items(), key=lambda x: x[1])[0]


def distribuir_partes(preferencia, taxas_acerto, total_partes=3):
    """
    Distribui as partes de conteúdo com base na preferência e taxas de acerto.
    
    Args:
        preferencia: Método preferido (texto, imagem ou video)
        taxas_acerto: Dicionário com taxas de acerto por método
        total_partes: Número total de partes a distribuir
        
    Returns:
        list: Lista com os métodos para cada parte
    """
    # Ordenar métodos por taxa de acerto
    metodos_ordenados = sorted(taxas_acerto.keys(), key=lambda m: taxas_acerto[m], reverse=True)
    
    # Inicializar lista de partes
    partes = []
    
    # Garantir que o método preferido receba pelo menos uma parte
    partes.append(preferencia)
    
    # Distribuir o restante das partes
    partes_restantes = total_partes - 1
    
    # Método preferido recebe mais uma parte
    if partes_restantes > 0:
        partes.append(preferencia)
        partes_restantes -= 1
    
    # Se ainda houver partes, o segundo método com maior taxa recebe uma parte
    if partes_restantes > 0:
        segundo_metodo = metodos_ordenados[1] if metodos_ordenados[0] == preferencia else metodos_ordenados[0]
        partes.append(segundo_metodo)
    
    return partes


def processar_dados(dados_json):
    """
    Processa os dados do aluno e retorna as partes de conteúdo em formato JSON.
    
    Args:
        dados_json: String JSON com os dados do aluno
        
    Returns:
        Dict[str, Any]: Resultado com as partes numeradas
    """
    try:
        # Carregar dados
        dados = json.loads(dados_json)
        
        # Calcular taxas de acerto
        taxas_acerto = calcular_taxas_acerto(dados)
        
        # Avaliar preferência de conteúdo usando a lógica fuzzy simplificada
        preferencia = avaliar_preferencia_conteudo(taxas_acerto)
        
        # Distribuir partes
        partes = distribuir_partes(preferencia, taxas_acerto)
        
        # Criar dicionário com partes numeradas
        partes_numeradas = {}
        for i, parte in enumerate(partes, 1):
            partes_numeradas[f"parte{i}"] = parte
        
        return {
            "partes": partes_numeradas
        }
    except Exception as e:
        return {"erro": str(e)}


if __name__ == "__main__":
    # Exemplo de uso
    exemplo = {
        "nu_acertos_texto": 25,
        "nu_erros_texto": 5,
        "nu_acertos_imagem": 10,
        "nu_erros_imagem": 10,
        "nu_acertos_video": 8,
        "nu_erros_video": 12
    }
    
    resultado = processar_dados(json.dumps(exemplo))
    print("Resultado do processamento:")
    print(json.dumps(resultado, indent=2))
