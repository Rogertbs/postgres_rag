# Benchmark vLLM — Guia completo

Guia prático para fazer testes de benchmark no vLLM medindo latência (p50, p99), capacidade de resposta e limite de usuários simultâneos (para descobrir quantos agentes aguenta antes de desconectar).

Baseado no repositório oficial: https://github.com/vllm-project/vllm/tree/main/benchmarks

---

## Arquivo ideal para o que você quer (p50, p99, usuários simultâneos, latência)

O arquivo principal é o **`benchmark_serving.py`**, mas ele foi migrado para a CLI. Hoje se usa:

```
vllm bench serve
```

Ele gera exatamente o relatório que você precisa — TTFT, TPOT, ITL com **Mean / Median / P99**, throughput de requisições e tokens. Exemplo de saída:

```
Mean TTFT (ms):     71.54      P99 TTFT (ms):   79.49
Mean TPOT (ms):      7.91      P99 TPOT (ms):    8.03
Mean ITL  (ms):      7.74      P99 ITL  (ms):    8.39
Request throughput (req/s): 1.73
```

Parâmetros-chave para o seu cenário:
- `--max-concurrency N` → limita usuários simultâneos (testar quantos agentes aguenta)
- `--request-rate X` → req/s (use `inf` para stress máximo)
- `--burstiness` → variabilidade do tráfego (menor = rajadas, maior = uniforme)
- `--ramp-up-strategy linear|exponential` → sobe a carga gradualmente até quebrar (acha o limite)
- `--num-prompts` → total de requisições
- `--save-result --save-detailed --result-dir ./log/` → gera o relatório em JSON

### Métricas que o relatório entrega

| Métrica | Significado |
|---|---|
| **TTFT** (Time To First Token) | Latência até o 1º token — sentido de "resposta" do sistema |
| **TPOT** (Time Per Output Token) | Tempo entre tokens (excluindo o 1º) — "velocidade de digitação" |
| **ITL** (Inter-Token Latency) | Latência entre tokens consecutivos — percebe engasgos |
| **Request throughput** | Requisições por segundo atendidas |
| **Output token throughput** | Tokens gerados por segundo |
| **Total token throughput** | Tokens (input + output) processados por segundo |

Cada uma vem com **Mean / Median / P99** (e você ainda tem P50 implícito no Median).

---

## Recomendação forte: use o GuideLLM

A própria vLLM diz na documentação que **para benchmark de produção o recomendado é o GuideLLM** (https://github.com/vllm-project/guidellm), porque ele gera relatório HTML/CSV/JSON automaticamente e faz **sweep automático** para achar o limite de saturação (exatamente o ponto onde agentes começam a desconectar):

```bash
pip install guidellm[recommended]
vllm serve <modelo>

guidellm benchmark \
  --target http://localhost:8000 \
  --profile kind=sweep \
  --max-seconds 60 \
  --data "kind=synthetic_text,prompt_tokens=256,output_tokens=128" \
  --detect-saturation
```

Gera:
- `benchmarks.html` — relatório visual com gráficos de distribuição de latência
- `benchmarks.csv` — planilha pronta para comparar runs
- `benchmarks.json` — detalhado para dashboards/regressão

Perfis de carga disponíveis:
- `synchronous` — requisições sequenciais
- `concurrent` — N usuários em paralelo
- `throughput` — capacidade máxima
- `constant` — req/s fixo
- `poisson` — req/s aleatório (mais realista)
- `sweep` — exploração automática de taxa (acha o limite)

---

## Fluxo completo para gerar relatório (com `vllm bench serve`)

### 1. Sobe o servidor

```bash
vllm serve NousResearch/Hermes-3-Llama-3.1-8B --port 8000
```

### 2. Baixa dataset ShareGPT (tráfego realista)

```bash
wget https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json
```

### 3. Teste com carga fixa (ex: 50 usuários simultâneos)

```bash
vllm bench serve \
  --backend vllm --model NousResearch/Hermes-3-Llama-3.1-8B \
  --endpoint /v1/completions \
  --dataset-name sharegpt \
  --dataset-path ShareGPT_V3_unfiltered_cleaned_split.json \
  --num-prompts 1000 \
  --max-concurrency 50 \
  --save-result --save-detailed --result-dir ./log/
```

### 4. Stress test para achar o limite (ramp-up)

```bash
vllm bench serve \
  --backend vllm --model NousResearch/Hermes-3-Llama-3.1-8B \
  --endpoint /v1/completions \
  --dataset-name sharegpt \
  --dataset-path ShareGPT_V3_unfiltered_cleaned_split.json \
  --num-prompts 1000 \
  --ramp-up-strategy linear \
  --ramp-up-start-rps 1 --ramp-up-end-rps 50 \
  --save-result --result-dir ./log/
```

### 5. Visualização extra (timeline interativa HTML)

```bash
vllm bench serve \
  --backend vllm --model NousResearch/Hermes-3-Llama-3.1-8B \
  --endpoint /v1/completions \
  --dataset-name sharegpt \
  --dataset-path ShareGPT_V3_unfiltered_cleaned_split.json \
  --num-prompts 1000 \
  --plot-timeline --plot-dataset-stats \
  --save-result --result-dir ./log/
```

### Estratégia para achar o limite de agentes

Faça varreduras com `--max-concurrency` em **10, 25, 50, 100, 200...** e compare o **P99 TTFT/ITL**. O ponto onde:
- P99 dispara (degradação brusca)
- aparecem erros/timeouts
- throughput para de crescer

...é o **limite de agentes simultâneos** que o servidor aguenta.

---

## Eficiência do MODELO (não só da VLLM)

Os outros arquivos úteis para medir eficiência do modelo em si:

| Arquivo / Comando | Mede |
|---|---|
| `vllm bench latency` (antigo `benchmark_latency.py`) | Latência pura do modelo, sem rede/servidor — desempenho bruto de geração |
| `vllm bench throughput` (`benchmark_throughput.py`) | Throughput offline em batch — tokens/s máximos que o modelo entrega |
| `benchmark_long_document_qa_throughput.py` | Eficiência com contextos longos (KV cache, atenção) |
| `benchmark_serving_structured_output.py` | Latência/throughput com saída JSON/gramática |
| `benchmark_prioritization.py` | Impacto de priorizar requisições |
| `benchmark_prefix_caching.py` | Ganho de cache de prefixo (system prompts repetidos) |

### Medindo qualidade + eficiência por tarefa

Use os datasets HuggingFace embutidos no `vllm bench serve`:

- `openai/gsm8k` — matemática/reasoning
- `openai/openai_humaneval` — código
- `philschmid/mt-bench` — conversa multi-turno
- `likaixin/InstructCoder` — código + speculative decoding
- `AI-MO/aimo-validation-aime` — modelos de reasoning (QwQ etc.)

Exemplo comparando eficiência do modelo em reasoning:

```bash
vllm bench serve --model Qwen/QwQ-32B \
  --dataset-name hf --dataset-path AI-MO/aimo-validation-aime \
  --num-prompts 80 --save-result --result-dir ./log/qwQ32/
```

Compare o `Output token throughput (tok/s)` e `P99 TTFT` entre modelos no mesmo dataset/hardware — isso mede eficiência do modelo, não só do servidor.

---

## Resumo da recomendação

- **Relatório de capacidade/latência com p50/p99 + limite de usuários**: use **GuideLLM** com `profile=sweep` + `--detect-saturation` (gera HTML automaticamente). Fallback: `vllm bench serve` com `--max-concurrency` + `--ramp-up-strategy`.
- **Eficiência bruta do modelo**: `vllm bench latency` e `vllm bench throughput`.
- **Eficiência por tipo de tarefa**: `vllm bench serve` com datasets HF (GSM8K, HumanEval, MT-Bench).

## Referências

- Repositório: https://github.com/vllm-project/vllm/tree/main/benchmarks
- GuideLLM: https://github.com/vllm-project/guidellm
- Doc CLI: https://docs.vllm.ai/en/latest/benchmarking/cli/
- CLI serve: https://docs.vllm.ai/en/latest/cli/bench/serve.html
- CLI latency: https://docs.vllm.ai/en/latest/cli/bench/latency.html
- CLI throughput: https://docs.vllm.ai/en/latest/cli/bench/throughput.html
