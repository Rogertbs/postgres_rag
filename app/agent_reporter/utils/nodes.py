from langchain_core.messages import SystemMessage, AnyMessage, HumanMessage, AIMessage
from typing import Literal
from datetime import datetime
#from .tools import model_with_tools
from .llm import model
from .state import ReporterState
import json

def buscador_noticia_bruta(state: dict):
    """Gera noticia ficticia via LLM, com a data do dia atual"""
    data_atual = datetime.now().strftime("%Y-%m-%d")
    resposta = model.invoke([
                                SystemMessage(
                                    content=f"Voce é um gerador de noticias ficticias de acordo com o assunto informado, retorne uma noticia bruta pronta para um redator resumir e criar. Sempre adicione a data de hoje {data_atual}"
                                ),
                                HumanMessage(content=f"Assunto: {state['assunto']}"),
                            ])
    return {
        "noticia_bruta": resposta.content,
        "tentativas": 0
    }

def resumidor_noticia(state: dict):
    """Resume a noticia e gera um titulo"""
    resposta = model.invoke([
        SystemMessage(
            content="""Faça um resumo da noticia em questao, gere um titulo para que fique formatada e de acordo para postar em um jornal.
            Regra: Reposta SEMPRE em JSON valido com esta estrutura exata:
            {"titulo": "...", "resumo": "..."}
            - titulo: ate 10 palavras, em MAIUSCULAS
            - resumo: 2-3 paragrafos
            - responda APENAS o JSON, sem texto antes nem depois"""),
        HumanMessage(content=f"Noticia: {state['noticia_bruta']}"),    
    ])
    
    try:
        # limpa respota
        texto = resposta.content.strip()
        # remove cercas markdown
        if texto.startswith("```"):
            texto = texto.split("\n", 1)[1] if "\n" in texto else texto
            texto = texto.split("```", 1)[0].strip()
        
        dados = json.loads(texto)
        titulo = dados["titulo"]
        resumo = dados["resumo"]
    except (json.JSONDecodeError, KeyError):
         # fallback: split por linha
        linhas = texto.split("\n", 1)
        titulo = linhas[0].strip()
        resumo = linhas[1].strip() if len(linhas) > 1 else texto
    
    return {
        "resumo": resumo,
        "titulo": titulo,
        "tentativas": state.get("tentativas", 0) + 1,
    }

def revisor_noticia(state: dict):
    """Recebe o resumo da noticia ja pronta para posta, e checa se esta ok para postar se nao faca o resumo novamente."""
    resposta = model.invoke([
        SystemMessage(content="""Voce é o cara que verifica se o resumo da noticia foi bem feito e ja pode postar, se nao foi bem feito solicita para fazer o resumo novamente apontanto os problemas
        Reponda APENAS 'positivo' ou 'negativo', e em uma linha explique o motivo.
        - positivo = pronta para publicar
        - negativo = precisa reescrever"""),
        HumanMessage(content=f"titulo: {state['titulo']}, {state['resumo']}"),
    ])
    print(f"Resposta bruta do LLM no REVISOR: {resposta.content!r} \n")
    texto = resposta.content.lower().strip()
    if "positivo" in texto[:20]:
        feedback = "positivo"
    elif "negativo" in texto[:20]:
        feedback = "negativo"
    else:
        # se não disse claramente, assume negativo
        feedback = "negativo"
    return {"feedback": feedback}

def entregador_noticia(state: dict):
    """Voce recebe uma noticia com titulo e resumo e faz a postagem dela"""
    return {
        "messages": [AIMessage(content=f"### {state['titulo']}\n\n{state['resumo']}")]
    }
