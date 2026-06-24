-- 1. Configurar o host do Ollama (ajuste a URL conforme necessário)
select set_config('ai.ollama_host', 'http://172.16.200.20:11434', false);

-- 2. Listar modelos disponíveis (use o schema "ai.")
SELECT *
FROM ai.ollama_list_models()
ORDER BY size DESC;

-- 3. Gerar texto com um modelo
select ai.ollama_generate
(
    'Qwen2.5:1.5b',
    'O que são LLMs. Responda brevemente'
)->'response';

-- 4. Gerar embedding
select ai.ollama_embed
(
    'nomic-embed-text',
    'O que são LLMs. Responda brevemente'
);

-- 5. Chat completo com mensagens
select ai.ollama_chat_complete
(
    'Qwen2.5:1.5b',
    jsonb_build_array(
        jsonb_build_object('role', 'system', 'content', 'Você é um assistente. Responda sempre em português.'),
        jsonb_build_object('role', 'user', 'content', 'Responda de forma breve o que é um LLM')
    ),
    _options=> jsonb_build_object(
        'seed', 42,
        'temperature', 0.6
    )
)->'message'->>'content' as model_response;
