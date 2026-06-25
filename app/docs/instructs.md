# LangGraph do Zero ao Avançado — Guia Orientado (com Ollama)

Refence: https://docs.langchain.com/oss/python/langgraph/quickstart#use-the-graph-api

> **Método deste guia:** eu não escrevo código para você. Eu explico a **lógica**,
> dou a **estrutura** (pseudo-código), aponto **quais APIs/imports procurar** e
> deixo **"Sua vez"** para você escrever. Assim você fixa o raciocínio do LangGraph.
>
> Objetivo prático: um pipeline de **notícias** (gera notícia fictícia → resume →
> revisa → aprova → entrega) cobrindo as **4 premissas**: **Streaming**,
> **Human-in-the-loop**, **Multi-Agente (Supervisor)** e **Cyclic Graphs**.
>
> LLM local: **Ollama** (`qwen2.5:1.5b`), mesmo stack do `rag_teste.py:32`.

---

## 0. Feedback sobre o seu pensamento (antes de começar)

O seu desenho mental está **correto no espírito**, com dois ajustes:

| Você imaginou | Ajuste | Por quê |
|---|---|---|
| "Agente que retorna a notícia ao usuário" | Vira **nó terminal de saída**, não agente | Agentes *decidem* via LLM. Entregar texto é um output, não uma decisão. |
| Supervisor com 4 agentes | Pipeline **linear + cíclico** não exige Supervisor | Supervisor é para roteamento **dinâmico**. Seu fluxo é fixo. Use Supervisor como **camada extra**. |

### Arquitetura que vamos construir (híbrida)

```
                    ┌─────────────────────────┐
   usuário ───────▶ │  SUPERVISOR (LLM)       │  (opcional) decide estratégia
                    └────────────┬────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │  NÓ: buscar_noticias    │  LLM gera notícia fictícia (estudo)
                    └────────────┬────────────┘
                                 ▼
                    ┌─────────────────────────┐
               ┌──▶ │  NÓ: resumir (agente)   │  gera título + resumo
               │    └────────────┬────────────┘
               │                 ▼
               │    ┌─────────────────────────┐
               │    │  NÓ: revisar (agente)   │  feedback: ok? ou ruim?
               │    └────────────┬────────────┘
               │                 │
               │   feedback=="negativo" ──┘  (CICLO / Revisão-Correção)
               │                 │ feedback=="positivo"
               │                 ▼
               │    ┌─────────────────────────┐
               │    │  NÓ: human_review (HITL)│  pausa p/ aprovação humana
               │    └────────────┬────────────┘
               │                 │ aprovado
               └─────────────────┘ não: reescrever
                                  ▼
                     ┌─────────────────────────┐
                     │  NÓ: entregar (output)   │  retorna ao usuário (STREAMING)
                     └─────────────────────────┘
```

Uma única aplicação exercita as **4 premissas**. Vamos construir passo a passo.

---

## 1. Instalação e Setup

```
pip install langgraph langchain-ollama langchain-core
# opcional: pip install langgraph-checkpoint-postgres psycopg[binary]
# opcional: pip install langgraph-cli   (para o Studio visual)
```

> Ollama já está em `http://172.16.200.20:11434` (`rag_teste.py:32`).

**Sua vez:** crie o arquivo `app/graph.py` vazio. Todo o código que você escrever
aqui partirá deste guia vai morar lá.

---

## 2. Conceitos fundamentais (decorar isso = 80% do LangGraph)

| Conceito | O que é | Analogia |
|---|---|---|
| **State** | Estrutura tipada que viaja pelo grafo. Cada nó lê e grava campos. | "Mala" passada de pessoa em pessoa |
| **Node** | Função `(state) -> state parcial`. Faz o trabalho. | Estação da malha ferroviária |
| **Edge** | Conexão fixa `A -> B`. | Trilho reto |
| **Conditional Edge** | Função `(state) -> nome_do_proximo_no`. Decide o caminho. | Agulhamento de trem |
| **Tool** | Função Python com `@tool`, exposta ao LLM. O LLM decide chamá-la. | Ferramenta no cinto do agente |
| **Checkpointer** | Memória persistente do state por `thread_id`. Habilita HITL. | "Save" de videogame |
| **Interrupt** | Pausa o grafo antes/depois de um nó. | Pausa do jogo |
| **START / END** | Nós especiais de entrada e saída. | Born/death do grafo |

### O esqueleto de TODO grafo (entenda, não copie)

Todo grafo LangGraph segue **4 passos fixos**. Pense neles como uma receita:

1. **Defina o State** — um `TypedDict` com os campos que circulam.
2. **Escreva os nós** — funções que recebem `state` e devolvem um **pedaço** do state (só os campos que mudaram).
3. **Monte o builder** — `StateGraph(State)`, registre os nós com `add_node`, ligue com `add_edge` / `add_conditional_edges`.
4. **Compile** — `builder.compile()` devolve um `graph` executável.

Pseudo-código do esqueleto:

```
class State(TypedDict):
    tema: str
    resultado: str

def meu_no(state):
    # lê state["tema"], processa, devolve SÓ o que mudou
    return {"resultado": <processado>}

builder = StateGraph(State)
builder.add_node("meu_no", meu_no)
builder.add_edge(START, "mei_no")
builder.add_edge("meu_no", END)
graph = builder.compile()
graph.invoke({"tema": "IA"})
```

**Sua vez #1 — o hello-world:**
- No `app/graph.py`, escreva o esqueleto acima com `tema` e `resultado`.
- O nó deve devolver `{"resultado": "Processado: " + state["tema"]}`.
- Importe de `langgraph.graph`: `StateGraph`, `START`, `END`.
- Rode com `python -m app.graph` e veja o state final impresso.

**Como verificar se está certo:** o `graph.invoke(...)` deve devolver um dict
com `tema` **e** `resultado`. Se devolver só `resultado`, faltou algo — lembre:
o LangGraph **mescla** o pedaço que o nó devolve com o state atual.

---

## 3. LLM + Tools com Ollama

### 3.1 Instanciar o LLM

Procure a classe `ChatOllama` em `langchain_ollama`. Ela recebe `model`,
`base_url` e `temperature`. Use o mesmo host de `rag_teste.py:32`.

**Pergunta-guia:** por que usamos `ChatOllama` (chat) e não `OllamaLLM` (completion)?
> R: tools e mensagens com papel (system/user/ai) exigem o formato **chat**.

### 3.2 Tool (vamos usar depois, no §6, como alternativa)

Uma **tool** é uma função Python comum + o decorator `@tool` de
`langchain_core.tools`. A **docstring** vira o "prompt" da tool — é como o LLM
sabe quando chamá-la. A assinatura tipada vira o schema JSON que o LLM vê.

Pseudo-código:
```
from langchain_core.tools import tool

@tool
def buscar_noticias_web(tema: str) -> str:
    """<EXPLIQUE ao LLM quando usar esta tool>"""
    # ... busca real (DuckDuckGo/Tavily) ...
    return <texto>
```

Para o LLM "enxergar" a tool: `llm.bind_tools([buscar_noticias_web])`.

### 3.3 Padrão ReAct (agente que decide chamar tool)

O loop ReAct em LangGraph tem **2 nós + 1 condicional**:

- **Nó agente:** chama o LLM com tools. A resposta pode ser texto final **ou** um
  `tool_calls` (pedidos para executar tools).
- **Nó tools:** executa as tools pedidas e devolve `ToolMessage`s.
- **Condicional:** olha a última mensagem. Se tem `tool_calls` → vai ao nó
  `tools`. Senão → vai ao `END`.

Atalhos prontos em `langgraph.prebuilt`: `ToolNode` (o nó tools) e
`ToolsCondition` (o condicional que decide tools-vs-END).

**Sua vez #2 — ReAct mínimo:**
- Crie uma tool `hora_atual()` que retorna a hora (use `datetime`).
- Monte um grafo: nó `agente` (chama `llm.bind_tools`) → condicional
  (`ToolsCondition` ou sua função) → nó `ToolNode([hora_atual])` → volta pro `agente`.
- Teste: pergunte "que horas são?" — o LLM deve chamar a tool e responder.

> No nosso app final (§6) o buscador **não** usará tool — vai gerar notícia
> fictícia direto via LLM (você pediu isso). Deixo a tool aqui para você
> **aprender o padrão**, que é a base de qualquer agente.

---

## 4. Visualizar o grafo (a "ferramenta front")

LangGraph gera **Mermaid** (texto) e **PNG** (imagem) direto do grafo compilado.

APIs a procurar no objeto `graph.get_graph()`:
- `.draw_mermaid()` → string Mermaid (cole em https://mermaid.live).
- `.draw_mermaid_png()` → bytes PNG.

**Sua vez #3:** no `__main__` do seu arquivo, chame os dois acima e salve o PNG.
Abra a imagem — você verá o desenho dos nós e edges. **Toda vez que adicionar um
nó, rode isso para ver o grafo crescer.**

### LangGraph Studio (UI visual oficial)

```
pip install langgraph-cli
langgraph dev          # UI em http://localhost:2024
```

Precisa de um `langgraph.json` na raiz do projeto mapeando o grafo. Procure a
estrutura no formato: `{"dependencies": ["."], "graphs": {"<nome>": "<caminho>:graph"}}`.

Na UI você roda o grafo, **vê o state em cada nó, pausa em interrupts (HITL),
aprova/rejeita, e vê o streaming** — é a "ferramenta front" que mostra o grafo
desenhado e executando.

---

## 5. As 4 premissas — uma a uma (estrutura + sua vez)

### 5.1 Streaming — `.astream()` e `.astream_events()`

Dois níveis de granularidade:

| Método | Streama o quê | Quando usar |
|---|---|---|
| `.astream(stream_mode="updates")` | o **diff** após cada nó | ver progresso por etapa |
| `.astream(stream_mode="values")` | o **state completo** a cada passo | debug do state |
| `.astream_events(version="v2")` | **tokens do LLM** em tempo real | UX de chatbot |

Estrutura do loop (pseudo):
```
async for evento in graph.astream_events(entrada, config=config, version="v2"):
    if evento["event"] == "on_chat_model_stream":
        # evento["data"]["chunk"].content é o token
        imprima_sem_quebrar_linha(token)
```

> Tudo aqui é **async** (`async for`). Rode com `asyncio.run(main())`.

**Sua vez #4:** transforme o `graph.invoke` do §2 em um `async` que usa
`.astream_events` e imprime tokens conforme aparecem.

### 5.2 Human-in-the-loop (HITL) — 3 ingredientes

1. **Checkpointer** — memória do state por `thread_id`. Comece com
   `MemorySaver` de `langgraph.checkpoint.memory` (em RAM; perde ao reiniciar).
2. **`interrupt_before=["<no>"]`** — passado em `compile(...)`. Pausa o grafo
   **antes** de executar esse nó.
3. **`thread_id`** — no `config = {"configurable": {"thread_id": "..."}}`.
   É o que identifica qual "save" retomar.

O fluxo de execução HITL é **sempre em 2 chamadas**:

```
# 1ª chamada: roda ATÉ a pausa (stream para ver progresso)
graph.stream(entrada, config=config)   # para antes do nó interrompido

# ... humano decide ...

# 2ª chamada: retoma, injetando a decisão no state
graph.invoke(Command(update={"approved": <bool>}), config=config)
```

> `Command` vem de `langgraph.types` — é a forma moderna de **atualizar state e
> retomar** ao mesmo tempo. Em versões antigas usava-se `graph.invoke(None, config)`.

**Persistência entre processos:** troque `MemorySaver` por `PostgresSaver` de
`langgraph.checkpoint.postgres` — você pode reusar o Postgres do projeto (porta
5434). Lembre de chamar `.setup()` para criar as tabelas de checkpoint.

**Sua vez #5:** adicione um nó `human_review` no seu grafo do §2 que só retorna
`{}` (não faz nada — é só ponto de pausa). Compile com `MemorySaver` +
`interrupt_before=["human_review"]`. Rode em 2 chamadas e confirme que pausa.

**Como verificar:** após a 1ª chamada, `graph.get_state(config).next` deve mostrar
`("human_review",)` — ou seja, o grafo está parado **antes** desse nó.

### 5.3 Multi-Agente — Supervisor Pattern

O **Supervisor** é um nó cuja função é **decidir qual agente vem a seguir**, via
LLM. Estrutura:

- Lista de agentes disponíveis: `["buscador", "resumidor", "revisor"]`.
- Nó `supervisor`: prompta o LLM com o state atual e pergunta "qual agente?".
  Grava a escolha em `state["next"]`.
- **Conditional edge** saindo do supervisor: retorna `state["next"]`.
- Cada agente volta para o supervisor (loop de coordenação).

Pseudo:
```
def supervisor(state):
    escolha = llm.invoke(prompt_com(state)).content.strip().lower()
    return {"next": escolha if escolha in agentes else fallback}

builder.add_edge(START, "supervisor")
builder.add_conditional_edges("supervisor", lambda s: s["next"], mapa_nomes)
for a in agentes:
    builder.add_edge(a, "supervisor")   # volta p/ supervisor
```

Atalho: pacote `langgraph-supervisor` com `create_supervisor(llm, agents=[...], prompt=...)`.

> **Para o app de notícias o Supervisor é OPCIONAL** — o fluxo é fixo. Use-o
> como camada extra decidindo *estratégia de busca* (fonte, idioma, foco).

### 5.4 Cyclic Graphs — loop de Revisão e Correção

Aqui está o coração do seu caso: **revisor manda de volta pro resumidor se a
notícia não ficou boa**. É um **ciclo** — LangGraph suporta nativamente.

A mágica está no **conditional edge saindo do revisor**:
```
def rota_revisao(state):
    if state["feedback"] == "negativo":
        return "resumidor"     # ← VOLTA: eis o ciclo
    return "entregar"
```

Ligue: `add_conditional_edges("revisor", rota_revisao, mapa)`.

**Proteção contra loop infinito:** adicione `tentativas: int` no state e corte:
```
def rota_revisao(state):
    if state.get("tentativas", 0) >= 3:
        return "entregar"      # desiste e entrega o melhor que tem
    return "resumidor" if state["feedback"] == "negativo" else "entregar"
```

**Pergunta-guia:** por que o ciclo é "revisor → resumidor" e não "revisor → revisor"?
> R: o revisor só **avalia**; quem **corrige** é o resumidor. O ciclo volta para
> quem tem poder de alterar o conteúdo.

**Sua vez #6:** no grafo do §2, crie `resumidor` → `revisor` → condicional que
volta ao `resumidor` se `feedback=="negativo"`. Imprima o Mermaid — você verá
uma **seta voltando** (o ciclo).

---

## 6. Aplicação completa — Pipeline de Notícias (você escreve)

Arquivo: `app/graph.py`. **Eu descrevo cada peça; você escreve.**

### Passo 1 — State

Pense nos dados que circulam. Você precisa de:
- `tema: str` — entrada do usuário.
- `noticias_brutas: str` — saída do buscador.
- `titulo: str` e `resumo: str` — saída do resumidor.
- `feedback: Literal["positivo", "negativo"]` — saída do revisor.
- `tentativas: int` — contador anti-loop.
- `approved: bool` — decisão humana.
- `messages: Annotated[list, add_messages]` — para o nó de saída (precisa do
  reducer `add_messages` de `langgraph.graph.message` para **acumular** em vez
  de sobrescrever).

> Armadilha: listas no state **sem** reducer são sobrescritas a cada nó. Para
> acumular mensagens, use `Annotated[list, add_messages]`.

**Sua vez:** escreva o `TypedDict` com esses campos.

### Passo 2 — LLM

Instancie `ChatOllama` com `model="qwen2.5:1.5b"`, `base_url` do
`OLLAMA_HOST` (env var com default de `rag_teste.py:32`), `temperature=0.3`.

### Passo 3 — Nó `buscador` (gera notícia fictícia via LLM, sem tool)

**Responsabilidade:** gerar UMA notícia fictícia e realista sobre `state["tema"]`.

Lógica:
- Monte um **prompt** pedindo: manchete em maiúsculas, data, 2-3 parágrafos,
  uma citação de fonte fictícia (nome + cargo).
- Chame `llm.invoke(prompt)` e pegue `.content`.
- Devolva `{"noticias_brutas": <texto>, "tentativas": 0}` (zera o contador no
  início da rodada).

> Por que `tentativas: 0` aqui? Porque cada nova busca reinicia o ciclo de
  revisão — faz sentido o contador voltar a zero.

**Sua vez:** escreva `no_buscador(state)`.

### Passo 4 — Nó `resumidor`

**Responsabilidade:** pegar as notícias brutas, filtrar e produzir título + resumo.

Lógica:
- Prompt: "Resuma em UM texto jornalístico curto, TÍTULO em maiúsculas na
  primeira linha, depois 2-3 parágrafos."
- Pegue `.content`, quebre na primeira `\n` → linha 0 = título, resto = resumo.
- Devolva `{"titulo": ..., "resumo": ..., "tentativas": state.get("tentativas",0)+1}`.

> O `+1` aqui é o que alimenta o contador anti-loop do §5.4.

**Sua vez:** escreva `no_resumidor(state)`. Dica: `str.split("\n", 1)` quebra só
na primeira quebra de linha.

### Passo 5 — Nó `revisor`

**Responsabilidade:** avaliar se a notícia ficou boa. Saída binária.

Lógica:
- Prompt: "Você é um editor. Avalie. Responda apenas 'positivo' ou 'negativo'."
- Pegue `.content.lower()`, verifique se começa com "positivo".
- Devolva `{"feedback": "positivo" ou "negativo"}`.

> Por que binário e não uma nota 0-10? Porque o condicional do ciclo precisa de
  uma decisão **discreta** para escolher o próximo nó.

**Sua vez:** escreva `no_revisor(state)`.

### Passo 6 — Condicional `rota_revisao` (O CICLO)

Lógica (com proteção anti-loop):
```
def rota_revisao(state):
    if state.get("tentativas", 0) >= 3:
        return "human_review"
    return "resumidor" if state["feedback"] == "negativo" else "human_review"
```

**Sua vez:** escreva a função. Pense: por que o limite manda para
`human_review` e não direto para `entregar`? (R: mesmo after 3 tentativas o
humano deve ter a palavra final sobre o "melhor esforço".)

### Passo 7 — Nó `human_review` (HITL)

**Responsabilidade:** nenhuma — é só **ponto de pausa**. A decisão vem de fora
(via `Command`).

Lógica: `def no_human_review(state): return {}`.

> O nó existe para que `interrupt_before=["human_review"]` tenha **onde** pausar.

### Passo 8 — Nó `entregar` (saída, não agente)

**Responsabilidade:** formatar e devolver a notícia ao usuário.

Lógica:
- Monte um `AIMessage` com `f"### {state['titulo']}\n\n{state['resumo']}"`.
- Devolva `{"messages": [AIMessage(...)]}`.

> Por que `AIMessage` e não string pura? Porque o campo `messages` é uma lista
  de mensagens tipadas — o protocolo do LangGraph.

**Sua vez:** escreva `no_entregar(state)`. Importe `AIMessage` de
`langchain_core.messages`.

### Passo 9 — Monte o grafo

Sequência de ligações:
```
START → buscador → resumidor → revisor
revisor --(rota_revisao)--> {resumidor | human_review}   ← CICLO
human_review → entregar → END
```

APIs: `builder.add_node`, `builder.add_edge`, `builder.add_conditional_edges`.
Compile com `checkpointer=MemorySaver()` e `interrupt_before=["human_review"]`.

**Sua vez:** monte e compile. Imprima o Mermaid — você deve ver a seta
`revisor → resumidor` (o ciclo).

### Passo 10 — Runner com Streaming + HITL

Escreva um `async def main()` que:
1. Define `config = {"configurable": {"thread_id": "user-1"}}`.
2. Roda `graph.astream_events({"tema": "inteligência artificial"}, config=config, version="v2")`
   em um `async for`, imprimindo tokens de `on_chat_model_stream`.
3. Após pausar (o loop termina quando o grafo para no interrupt), pede
   `input("Aprovar? [s/n]: ")`.
4. Retoma com `graph.invoke(Command(update={"approved": decisao=="s"}), config=config)`.

Rode com `asyncio.run(main())`.

**Como verificar o HITL:** após o `astream_events` terminar (pela 1ª vez),
`graph.get_state(config).next` deve ser `("human_review",)`.

### Passo 11 — (Opcional) Supervisor

Troque `START → buscador` por `START → supervisor → {buscador|...}` usando o
§5.3. O supervisor decide, por exemplo, se busca em português/inglês ou qual
foco dar ao tema. Cada agente volta para o supervisor.

---

## 7. Checklist das 4 premissas no seu app

| Premissa | Onde aparece |
|---|---|
| **Streaming** | `.astream_events(version="v2")` no runner |
| **Human-in-the-loop** | `interrupt_before=["human_review"]` + `MemorySaver` + `Command(update=...)` |
| **Cyclic Graphs** | `add_conditional_edges("revisor", rota_revisao)` voltando ao `resumidor` |
| **Multi-Agente (Supervisor)** | Passo 11 (opcional): nó supervisor + conditional de roteamento |

---

## 8. Ordem sugerida para praticar (cada item = um commit)

1. Esqueleto de 1 nó (§2). Veja o Mermaid.
2. Adicione 2 nós + 1 conditional edge simples. Veja o desenho mudar.
3. Crie uma `@tool` + agente ReAct (`bind_tools` + `ToolNode` + `ToolsCondition`).
4. Ative streaming com `.astream_events`.
5. Ative HITL com `MemorySaver` + `interrupt_before`.
6. Adicione o ciclo de revisão (revisor → resumidor).
7. (Opcional) troque o início por Supervisor.
8. Troque `MemorySaver` por `PostgresSaver` (reaproveita o Postgres do projeto).
9. Suba o LangGraph Studio (`langgraph dev`) e rode tudo na UI visual.

---

## 9. Armadilhas comuns (consulte quando travar)

- **Loop infinito**: sempre coloque `tentativas >= N` nos condicionais cíclicos.
- **Reducer esquecido**: listas no state (ex.: `messages`) precisam de
  `Annotated[list, add_messages]`, senão são **sobrescritas** em vez de acumular.
- **`interrupt_before` sem checkpointer**: erro em tempo de compilação.
- **`.invoke` vs `.stream` em HITL**: `.invoke` só retorna o state **final**;
  para HITL você **precisa** de `.stream`/`.astream` para receber os pedaços até
  a pausa.
- **Tool sem docstring**: o LLM não sabe quando usá-la. A docstring é o prompt da tool.
- **`thread_id` esquecido**: sem ele o checkpointer não sabe qual conversa retomar.
- **Nó que devolve state inteiro**: devolva **só o que mudou**. Devolver o state
  todo pode causar bugs sutis com reducers.

---

## 10. Resposta final ao seu pensamento

> "meu pensamento está ok ou dá pra ajustar?"

**Está ok.** Ajustes mínimos:

1. O 4º item ("retorna ao usuário") vira **nó de saída**, não agente.
2. Não force **Supervisor** se o fluxo é fixo — use-o só como camada extra.
3. Para fins de **estudo** o app gera notícia **fictícia** via LLM (sem tool) —
   roda 100% offline. Para notícias **reais**, troque o `no_buscador` por uma
   `@tool` de busca (DuckDuckGo/Tavily). É onde **tools + LangGraph** brilham.

Concluindo os **11 passos do §6** você terá um app funcional cobrindo as 4
premissas, rodando 100% local com Ollama, e visualizável em Mermaid/PNG e no
LangGraph Studio. **Escrevendo você mesmo, a lógica fixa.**

---

# Referência Rápida — Tools, Nodes e Edges

> Guia de bolso para decidir **quando usar o quê**. Consulte quando travar.

---

## R.1 Tools — quando usar

**Regra de ouro:** use uma tool quando o LLM **não consegue fazer sozinho** e
precisa **decidir** se chama.

| Precisa de tool? | Exemplo |
|---|---|
| **Sim** — LLM não tem acesso | buscar web, data/hora atual, query em DB, chamar API externa, calculator precisa |
| **Não** — LLM faz sozinho | gerar texto, resumir, traduzir, classificar, escrever código |

### Casos de uso reais

```python
@tool
def buscar_web(query: str) -> str:
    """Busca na internet quando precisa de informação atual."""
    # DuckDuckGo / Tavily / SerpAPI

@tool
def query_db(sql: str) -> str:
    """Consulta o banco quando precisa de dados internos."""
    # psycopg / SQLAlchemy

@tool
def enviar_email(destino: str, corpo: str) -> str:
    """Envia email — ação crítica, normalmente com HITL antes."""
    # SMTP / SendGrid
```

### Quando **NÃO** usar tool

```python
# ❌ ERRADO — isso é um nó, não uma tool
@tool
def resumir(texto: str) -> str:
    return llm.invoke(f"Resuma: {texto}")

# ✅ CERTO — o LLM já sabe resumir, é só chamar direto num nó
def no_resumidor(state):
    resp = llm.invoke([SystemMessage(...), HumanMessage(content=state["texto"])])
    return {"resumo": resp.content}
```

### Padrão de uso: ReAct (agente que decide)

```
pergunta → LLM.decide() → precisa de info? → chama tool → observa → LLM.decide() → responde
```

Sempre que tiver tool, precisa de:
- `bind_tools([...])` no LLM
- `ToolNode(tools)` como nó executor
- Condicional que olha `tool_calls` → vai pro nó tools ou pro END

---

## R.2 Nodes — quando e como

**Node = uma etapa que transforma o state.** Cada nó faz **uma coisa** e devolve
**só o que mudou**.

### Quando criar um nó

| Situação | Cria nó? |
|---|---|
| Chamar LLM pra gerar/classificar/resumir | **Sim** |
| Executar lógica sem LLM (formatar, contar, validar) | **Sim** |
| Pausar pra aprovação humana (HITL) | **Sim** (nó vazio que só marca pausa) |
| Uma decisão de roteamento | **Não** — isso é condicional (edge), não nó |

### 3 tipos de nó

```python
# TIPO 1 — Nó com LLM (o mais comum)
def no_buscador(state):
    resp = llm.invoke([SystemMessage(...), HumanMessage(content=state["assunto"])])
    return {"noticia_bruta": resp.content}

# TIPO 2 — Nó sem LLM (lógica pura)
def no_entregador(state):
    return {"messages": [AIMessage(content=f"### {state['titulo']}\n\n{state['resumo']}")]}

# TIPO 3 — Nó de pausa HITL (não faz nada, só existe pra ser interrompido)
def human_review(state):
    return {}
```

### Casos de uso por tipo

| Tipo | Caso de uso |
|---|---|
| **Com LLM** | buscador, resumidor, revisor, tradutor, classificador, gerador |
| **Sem LLM** | formatar output, contador, validador de schema, router por regra fixa |
| **HITL** | aprovação antes de publicar/enviar/cobrar |

### Regra mental

> Um nó **não decide** o caminho. Ele só transforma state. Quem decide o próximo
> passo é o **edge**.

---

## R.3 Edges — fixa vs condicional

### Edge fixa (`add_edge`) — caminho sempre igual

```python
builder.add_edge("buscador", "resumidor")   # depois de buscar, sempre resume
```

**Quando:** o próximo passo **nunca muda**, independente do state.

### Edge condicional (`add_conditional_edges`) — caminho depende do state

```python
def rota_revisao(state):
    if state["feedback"] == "negativo":
        return "resumidor"     # volta (CICLO)
    return "human_review"      # segue

builder.add_conditional_edges("revisor", rota_revisao)
```

**Quando:** o próximo passo **depende** de algo no state (feedback, decisão do
LLM, contador, aprovação).

### Comparação direta

| | Edge fixa | Edge condicional |
|---|---|---|
| **API** | `add_edge(A, B)` | `add_conditional_edges(A, função)` |
| **Decisão** | sempre vai pra B | função olha state e escolhe |
| **Ciclo possível?** | não (só A→B) | **sim** (pode voltar A→A) |
| **Caso típico** | pipeline linear | roteamento, loops, branches |

### Casos de uso de cada

```python
# EDGE FIXA — pipeline linear
builder.add_edge(START, "buscador")
builder.add_edge("buscador", "resumidor")      # sempre
builder.add_edge("entregador", END)             # sempre termina

# EDGE CONDICIONAL — ciclo de revisão
builder.add_conditional_edges("revisor", rota_revisao)  # depende do feedback

# EDGE CONDICIONAL — HITL (aprovou/reprovou)
builder.add_conditional_edges("human_review", rota_aprovacao)  # depende de approved

# EDGE CONDICIONAL — ReAct (tem tool_calls ou não)
builder.add_conditional_edges("agente", ToolsCondition)  # "tools" ou END

# EDGE CONDICIONAL — roteamento por tipo
def rota_suporte(state):
    if "fatura" in state["mensagem"]:
        return "agente_financeiro"
    if "tecnico" in state["mensagem"]:
        return "agente_tecnico"
    return "agente_geral"
builder.add_conditional_edges("classificador", rota_suporte)
```

### Quando o ciclo (loop) entra

O ciclo **só existe** em edge condicional — quando a função retorna o nome de um
nó **anterior**:

```python
def rota_revisao(state):
    return "resumidor" if state["feedback"] == "negativo" else "entregar"
    #         ^^^^^^^^^^^^ nó ANTERIOR = ciclo (volta)
```

Sempre proteja com contador anti-loop:
```python
if state.get("tentativas", 0) >= 3:
    return "entregar"   # desiste do ciclo
```

---

## R.4 Árvore de decisão — quando usar o quê

```
Precisa de algo que o LLM não faz sozinho?
├── SIM → @tool + ToolNode + condicional (ReAct)
└── NÃO → nó que chama llm.invoke() direto

O próximo passo é sempre o mesmo?
├── SIM → add_edge (fixa)
└── NÃO → add_conditional_edges (condicional)

O condicional retorna um nó anterior?
├── SIM → é um CICLO (proteja com contador)
└── NÃO → é um branch normal

É uma decisão de roteamento (qual agente/caminho)?
├── SIM → é condicional (edge), NÃO é nó
└── NÃO → se for transformação, é nó
```
