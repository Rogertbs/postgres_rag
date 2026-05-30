select set_config('ai.ollama_host', 'http://host.docker.internal:11434', false);

SELECT *
FROM ollama_list_models()
ORDER BY size DESC;

select ollama_generate
(
    'llama3',
    'O que são LLMs. Responda brevemente'
)->'response';

select ollama_embed
(
    'llama3',
    'O que são LLMs. Responda brevemente'
);

select ollama_chat_complete
(
    'llama3',
    jsonb_build_array(
        jsonb_build_object('role', 'system', 'content', 'Você é um assistente. Responda sempre em português.'),
        jsonb_build_object('role', 'user', 'content', 'Responda de forma breve o que é um LLM')
    ),
    _options=> jsonb_build_object(
        'seed', 42,
        'temperature', 0.6
    )
)->'message'->>'content' as model_response;
