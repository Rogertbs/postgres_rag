from langchain.chat_models import init_chat_model

# Definindo modelo LLM

model = init_chat_model(
    "qwen2.5:1.5b",
    model_provider="ollama",
    base_url="http://172.16.200.20:11434",
    temperature=0,
)

