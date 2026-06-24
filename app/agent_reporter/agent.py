from .utils.state import ReporterState
from .utils.nodes import buscador_noticia_bruta, resumidor_noticia, revisor_noticia, entregador_noticia
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Literal

# Funcao condicional q decide o caminho depois do revisor
def rota_revisao(state) -> Literal["resumidor_noticia", "human_review"]:
    if state.get("tentativas", 0) >= 3:
        return "human_review"
    return "resumidor_noticia" if state["feedback"] == "negativo" else "human_review"

# rota de aprovacao humana
def rota_aprovacao(state) -> Literal["entregador_noticia", "resumidor_noticia"]:
    if state.get("approved"):
        return "entregador_noticia"
    return "resumidor_noticia"

# Nó HITL (marca pausa)
def human_review(state):
    return {}

## Builder
builder = StateGraph(ReporterState)
builder.add_node("buscador_noticia_bruta", buscador_noticia_bruta)
builder.add_node("resumidor_noticia", resumidor_noticia)
builder.add_node("revisor_noticia", revisor_noticia)
builder.add_node("human_review", human_review)
builder.add_node("entregador_noticia", entregador_noticia)

# Edges
builder.add_edge(START, "buscador_noticia_bruta")
builder.add_edge("buscador_noticia_bruta", "resumidor_noticia")
builder.add_edge("resumidor_noticia", "revisor_noticia")
builder.add_conditional_edges("revisor_noticia", rota_revisao) # <- ciclo
#builder.add_edge("human_review", "entregador_noticia")
builder.add_conditional_edges("human_review", rota_aprovacao)
builder.add_edge("entregador_noticia", END)

# compile com checkpointer + HITL 
agent = builder.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["human_review"]
)
    
    
