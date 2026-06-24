# RAG PG — Chatbot Privado + Agentes LangGraph

Repositório com **dois experimentos** que compartilham o mesmo stack (PostgreSQL + pgvector + Ollama):

1. **RAG interativo** (`rag_teste.py`) — busca vetorial + geração de resposta via LLM.
2. **Agent Reporter** (`app/agent_reporter/`) — pipeline de notícias fictícias com **LangGraph**, exercitando as 4 premissas: Streaming, Human-in-the-loop, Multi-Agente (Supervisor) e Cyclic Graphs.

> Guia de estudo LangGraph em `app/docs/instructs.md` — do zero ao avançado, com Ollama.

---

## Visão geral

```
rag_pg/
├── rag_teste.py              # [1] RAG interativo (PostgreSQL + pgvector)
├── app/                      # [2] Aplicação LangGraph
│   ├── main.py               #   Runner do agent_reporter (terminal)
│   ├── docs/instructs.md     #   Guia de estudo LangGraph
│   └── agent_reporter/       #   Agente "Reporter" de notícias
│       ├── agent.py          #     Montagem + compile do grafo
│       └── utils/
│           ├── state.py      #     State (TypedDict + reducers)
│           ├── nodes.py      #     Nós (buscador, resumidor, revisor, entregador)
│           ├── llm.py        #     Instância do LLM (Ollama)
│           └── tools.py      #     Tools (data_atual, etc)
├── seed_data.sql             # Dados de teste do RAG
├── Dockerfile                # PostgreSQL 18 + pgvector
├── docker-compose.yaml       # Orquestração do container
└── ...
```

---

# Parte 1 — RAG Interativo (rag_teste.py)

Serviço de banco de dados vetorial para chatbot privado, utilizando PostgreSQL 18 com as extensões **pgvector** (armazenamento e busca de embeddings) e **pgai** (integração com Ollama para geração de embeddings e LLM).

---

## Arquitetura — Fluxo RAG (rag_teste.py)

```
┌──────────────────────────────────────────────────────────────┐
│  Usuário digita a pergunta                                   │
│  Ex: "Onde nasce o rio Gange?"                               │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  1. Embedding da pergunta                                    │
│     Ollama (nomic-embed-text) → vetor 768 dimensões          │
│     Servidor remoto: $OLLAMA_HOST                            │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  2. RETRIEVAL — Busca por similaridade                       │
│     PostgreSQL + pgvector (Docker :5434)                     │
│     SELECT ... ORDER BY embedding <=> pergunta LIMIT 3       │
│     Distância cosseno (<=>) — quanto menor, mais similar     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  3. PREVIEW — Documentos recuperados                         │
│     Mostra similaridade de cada documento                    │
│     Usuário vê se os resultados fazem sentido                │
│     Confirma com [Enter] ou pula com [n]                     │
└────────────────────────┬─────────────────────────────────────┘
                         │ (usuário confirma)
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  4. AUGMENTED + GENERATION                                   │
│     Monta prompt: CONTEXTO + PERGUNTA                        │
│     Ollama (qwen2.5:1.5b) gera a resposta                    │
│     Ex: "O Gange nasce nas geleiras de Uttarakhand..."       │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  Resposta exibida no terminal                                │
└──────────────────────────────────────────────────────────────┘
```

### Componentes

| Camada         | Tecnologia                        | Onde roda        |
|----------------|-----------------------------------|------------------|
| Embedding      | Ollama + nomic-embed-text (768d)  | Servidor remoto  |
| Busca vetorial | PostgreSQL 18 + pgvector          | Docker (:5434)   |
| LLM / Geração  | Ollama + qwen2.5:1.5b             | Servidor remoto  |
| Orquestração   | Python (ollama, pgvector, psycopg2) | Script local   |

---

## Estrutura do Projeto

```
rag_pg/
├── rag_teste.py            # [RAG] Script principal — RAG interativo via terminal
├── app/                    # [LangGraph] Aplicação de agentes
│   ├── main.py             #   Runner do agent_reporter
│   ├── docs/instructs.md   #   Guia de estudo LangGraph
│   └── agent_reporter/     #   Agente Reporter (notícias)
├── seed_data.sql           # Popula o banco com dados de teste (Himalaia indiano)
├── Dockerfile              # Imagem PostgreSQL 18 + pgvector + pgai
├── docker-compose.yaml     # Orquestração do container
├── activate-extension.sql  # Ativa extensões no startup do banco
├── create_tables.sql       # Criação da tabela items
├── embed_test.sql          # Testes de embedding e similaridade via SQL
├── pg_hba.conf             # Configuração de autenticação
└── postgres_data/          # Volume de dados persistente
```

---

## Stack

| Componente    | Tecnologia                     |
|---------------|--------------------------------|
| Banco         | PostgreSQL 18 + pgvector       |
| Embedding     | Ollama (nomic-embed-text, 768d)|
| LLM           | Ollama (qwen2.5:1.5b)         |
| Container     | Docker + Docker Compose        |
| Script        | Python 3 + ollama + pgvector + psycopg2 |

---

## Pré-requisitos

- Docker e Docker Compose instalados
- [Ollama](https://ollama.com) rodando em servidor remoto com os modelos:
  - `nomic-embed-text` (embedding)
  - `qwen2.5:1.5b` (LLM)
- Python 3 com as bibliotecas:
  ```bash
  pip3 install pgvector psycopg2-binary ollama
  ```

---

## Como subir

```bash
cd /ez/services/rag_pg
docker compose up -d --build
```

O banco estará disponível em `localhost:5434`:
- **Database:** `vectordb`
- **Usuário:** `postgres`
- **Senha:** `postgres`

---

## Como testar

### Via script Python (recomendado)

```bash
# Aponte para o servidor Ollama remoto
export OLLAMA_HOST=http://<IP_DO_SERVIDOR>:11434

# Execute o RAG interativo
python3 rag_teste.py
```

O fluxo interativo:
1. Digite uma pergunta sobre o Himalaia
2. Veja os documentos recuperados com similaridade
3. Confirme [Enter] para gerar a resposta via LLM, ou [n] para pular

### Variáveis de ambiente

| Variável     | Default                  | Descrição                    |
|-------------|--------------------------|------------------------------|
| OLLAMA_HOST | http://172.16.200.20:11434 | Servidor Ollama remoto     |
| DB_HOST     | localhost                | Host do PostgreSQL           |
| DB_PORT     | 5434                     | Porta do PostgreSQL          |
| DB_NAME     | vectordb                 | Nome do banco                |
| DB_USER     | postgres                 | Usuário do banco             |
| DB_PASS     | postgres                 | Senha do banco               |

### Via SQL (testes diretos no banco)

```bash
# Popular com dados de teste
docker exec -i postgres-ai-postgres-1 psql -U postgres -d vectordb < seed_data.sql

# Testes de embedding e similaridade
docker exec -i postgres-ai-postgres-1 psql -U postgres -d vectordb < embed_test.sql
```

---

## Comandos úteis

```bash
# Ver logs
docker compose logs -f

# Derrubar e limpar volumes
docker compose down -v

# Recriar do zero
docker compose up -d --build --force-recreate
```

---

# Parte 2 — Agent Reporter (LangGraph)

Pipeline de **notícias fictícias** geradas por IA, orquestrado com **LangGraph** sobre o **Ollama** (`qwen2.5:1.5b`). Exercita as **4 premissas** do framework.

## Arquitetura — Fluxo do grafo

```
                    ┌─────────────────────────┐
   usuário ───────▶ │  buscador_noticia_bruta │  LLM gera notícia fictícia
                    └────────────┬────────────┘
                                 ▼
                    ┌─────────────────────────┐
               ┌──▶ │  resumidor_noticia      │  gera título + resumo (JSON)
               │    └────────────┬────────────┘
               │                 ▼
               │    ┌─────────────────────────┐
               │    │  revisor_noticia        │  feedback: positivo/negativo
               │    └────────────┬────────────┘
               │                 │
               │   feedback=="negativo" ──┘  (CICLO / Revisão-Correção)
               │                 │ feedback=="positivo"
               │                 ▼
               │    ┌─────────────────────────┐
               │    │  human_review (HITL)    │  pausa p/ aprovação humana
               │    └────────────┬────────────┘
               │                 │ aprovado
               └─────────────────┘ não: volta pro resumidor
                                 ▼
                    ┌─────────────────────────┐
                    │  entregador_noticia     │  retorna ao usuário (output)
                    └─────────────────────────┘
```

## As 4 premissas cobertas

| Premissa | Onde aparece |
|---|---|
| **Cyclic Graphs** | `add_conditional_edges("revisor_noticia", rota_revisao)` volta ao resumidor |
| **Human-in-the-loop** | `interrupt_before=["human_review"]` + `MemorySaver` + `Command(update=...)` |
| **Streaming** | `agent.stream(...)` no runner (`app/main.py`) |
| **Multi-Agente (Supervisor)** | (opcional) nó supervisor roteando entre agentes |

## Como rodar

```bash
cd /ez/services/rag_pg/app
python3 main.py
```

O fluxo interativo:
1. O grafo gera uma notícia fictícia sobre o tema.
2. O resumidor cria título + resumo (em JSON).
3. O revisor avalia (positivo/negativo). Se negativo, **volta pro resumidor** (ciclo).
4. O grafo **pausa** para aprovação humana: `Aprovar? [s/n]`
   - `s` → entregador publica a notícia final.
   - `n` → volta pro resumidor para reescrever.
5. Limite anti-loop: 3 tentativas (depois disso, segue pra aprovação mesmo assim).

## Estrutura do agent_reporter

| Arquivo | Responsabilidade |
|---|---|
| `agent.py` | Monta o `StateGraph`, registra nós, liga edges, `compile()` → variável `agent` |
| `utils/state.py` | `ReporterState` (TypedDict) — campos que circulam no grafo |
| `utils/nodes.py` | Funções dos nós: `buscador_noticia_bruta`, `resumidor_noticia`, `revisor_noticia`, `entregador_noticia` |
| `utils/llm.py` | Instância do `ChatOllama` (via `init_chat_model`) |
| `utils/tools.py` | Tools (`@tool`) — ex.: `data_atual` (uso opcional, pra aprender ReAct) |

## Guia de estudo

O documento `app/docs/instructs.md` contém o passo a passo pedagógico de LangGraph do zero ao avançado, com as 4 premissas explicadas isoladamente e a aplicação completa desenhada passo a passo.

## Observabilidade (opcional)

Para visualizar traces do grafo, configure o **LangSmith** via env vars antes de rodar:

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<sua-key>
export LANGSMITH_PROJECT=App-Langgraph-Learning
```

> Veja `app/.env-sample` para o template. **Nunca commite a key real** (use `.env-langsmith` ignorado pelo `.gitignore`).
