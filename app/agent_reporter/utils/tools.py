# from langchain_core.tools import tool
# from datetime import datetime
# from .llm import model


# # Definição de tools

# @tool
# def data_atual() -> str:
#     """Retorna a data  de hoje no formato ISO (YYYY-MM-DD). Use quando precisar saber a data atual."""
#     return datetime.now().strftime("%Y-%m-%d")

# tools = [data_atual]
# tools_by_name = {tool.name: tool for tool in tools}
# model_with_tools = model.bind_tools(tools)