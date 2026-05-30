"""
RAG (Retrieval-Augmented Generation) - Teste Interativo
========================================================
Fluxo RAG:
  1. Usuário digita uma pergunta
  2. A pergunta é convertida em embedding via Ollama (nomic-embed-text)
  3. PostgreSQL (pgvector) busca os documentos mais similares por distância cosseno
  4. Os trechos recuperados são injetados como contexto no prompt do LLM
  5. Ollama gera a resposta final baseada no contexto + pergunta
"""

import os
import sys
from typing import List, Tuple

import ollama
import psycopg2
from pgvector.psycopg2 import register_vector

# ============================================================
# CONFIGURAÇÕES — ajuste conforme seu ambiente
# ============================================================

# PostgreSQL (Docker — container postgres-ai-postgres-1)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5434")
DB_NAME = os.getenv("DB_NAME", "vectordb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

# Ollama (servidor de embeddings e LLM)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://172.16.200.20:11434")
EMBED_MODEL = "nomic-embed-text"  # modelo de embedding (768 dimensões)
LLM_MODEL = "qwen2.5:1.5b"            # modelo de linguagem para gerar resposta

# Quantos documentos similares recuperar antes de gerar a resposta
TOP_K = 3

# ============================================================
# CONEXÃO COM O POSTGRESQL (Docker)
# ============================================================

print("[1/4] Conectando ao PostgreSQL (Docker)...")
try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
    )
    register_vector(conn)  # habilita suporte ao tipo vector no psycopg2
    print(f"      Conectado! Banco: {DB_NAME} na porta {DB_PORT}")
except Exception as e:
    print(f"      ERRO ao conectar no PostgreSQL: {e}")
    print("      Verifique se o container Docker está rodando:")
    print("        docker ps | grep postgres-ai")
    sys.exit(1)

# ============================================================
# CONEXÃO COM O OLLAMA
# ============================================================

print("[2/4] Verificando Ollama...")
try:
    ollama_client = ollama.Client(host=OLLAMA_HOST)

    # Verifica se os modelos estão disponíveis
    response = ollama_client.list()
    if hasattr(response, "models"):
        # ollama >= 0.4.0 retorna objetos com atributo .model
        modelos = [m.model for m in response.models]
    else:
        # fallback: dict com chave "models"
        modelos = [m["name"] for m in response["models"]]

    if EMBED_MODEL not in modelos:
        print(f"      Modelo de embedding '{EMBED_MODEL}' não encontrado. Baixando...")
        ollama_client.pull(EMBED_MODEL)

    if LLM_MODEL not in modelos:
        print(f"      Modelo LLM '{LLM_MODEL}' não encontrado. Baixando...")
        ollama_client.pull(LLM_MODEL)

    print(f"      Ollama OK! Embed: {EMBED_MODEL} | LLM: {LLM_MODEL}")
except Exception as e:
    print(f"      ERRO ao conectar no Ollama: {e}")
    print("      Dicas:")
    print("        - Ollama rodando?  curl http://localhost:11434/api/tags")
    print("        - Se estiver em Docker, use: export OLLAMA_HOST=http://IP:11434")
    sys.exit(1)


# ============================================================
# FUNÇÕES DO RAG
# ============================================================

def gerar_embedding(texto: str) -> List[float]:
    """
    Converte um texto em um vetor de embedding usando Ollama.
    Esse vetor representa o significado semântico do texto.
    """
    resposta = ollama_client.embed(model=EMBED_MODEL, input=texto)
    return resposta["embeddings"][0]


def buscar_similares(embedding: List[float], top_k: int = TOP_K) -> List[Tuple[str, float]]:
    """
    ===== ETAPA DE RETRIEVAL (R do RAG) =====
    Busca no PostgreSQL os documentos cujo embedding é mais
    próximo (distância cosseno) do embedding da pergunta.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT description, 1 - (embedding <=> %s::vector) AS similarity
            FROM items
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (embedding, embedding, top_k),
        )
        return [(row[0], row[1]) for row in cur.fetchall()]


def etapa_retrieval(pergunta: str) -> List[Tuple[str, float]]:
    """
    ===== RETRIEVAL (R do RAG) =====
    Converte pergunta em embedding e busca documentos similares no PostgreSQL.
    Retorna lista de (descricao, similaridade).
    """
    print("[3/4] Gerando embedding da pergunta...")
    embedding_pergunta = gerar_embedding(pergunta)

    print(f"[4/4] Buscando os {TOP_K} documentos mais similares...")
    return buscar_similares(embedding_pergunta, top_k=TOP_K)


def etapa_generation(pergunta: str, trechos: List[Tuple[str, float]]) -> str:
    """
    ===== AUGMENTED + GENERATION (AG do RAG) =====
    Monta o prompt com os trechos recuperados como contexto
    e gera a resposta via LLM (Ollama).
    """
    contexto = "\n\n".join([f"- {desc}" for desc, _ in trechos])

    prompt = f"""Use o contexto abaixo para responder a pergunta. Se o contexto for relevante, responda com suas próprias palavras usando as informações fornecidas. Se não houver informação relevante, diga que não sabe.

CONTEXTO:
{contexto}

PERGUNTA: {pergunta}

RESPOSTA:"""

    resposta = ollama_client.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.3},
    )

    return resposta["message"]["content"]


# ============================================================
# LOOP INTERATIVO
# ============================================================

print()
print("=" * 60)
print("  RAG INTERATIVO — Digite perguntas para testar")
print("  Documentos na base: Himalaia, Royal Enfield Himalayan,")
print("  IA, Exercícios Físicos")
print("  Digite 'sair' para encerrar.")
print("=" * 60)
print()

while True:
    try:
        pergunta = input("🤖 Sua pergunta: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAté mais!")
        break

    if not pergunta:
        continue

    if pergunta.lower() in ("sair", "exit", "quit"):
        print("Até mais!")
        break

    print()

    # ===== ETAPA 1: RETRIEVAL — busca documentos similares =====
    trechos = etapa_retrieval(pergunta)

    if not trechos:
        print("  Nenhum documento relevante encontrado na base.")
        print()
        continue

    # Mostra prévia dos documentos recuperados
    print()
    print("  📄 Documentos recuperados (Retrieval):")
    print("  " + "-" * 50)
    for i, (desc, sim) in enumerate(trechos, 1):
        print(f"  {i}. [similaridade: {sim:.4f}] {desc[:80]}{'...' if len(desc) > 80 else ''}")
    print("  " + "-" * 50)

    # Pergunta se quer gerar resposta ou refinar a busca
    resposta = input("\n  Gerar resposta com LLM? [S/n] ").strip().lower()
    if resposta in ("n", "no", "nao", "não"):
        print("  Ok, busca encerrada. Tente outra pergunta.\n")
        continue

    # ===== ETAPA 2: AUGMENTED + GENERATION =====
    print("\n  Gerando resposta via LLM...")
    resposta_llm = etapa_generation(pergunta, trechos)
    print(f"  🤖 Resposta: {resposta_llm}")
    print()
