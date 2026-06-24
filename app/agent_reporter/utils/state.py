from typing_extensions import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages
import operator

class ReporterState(TypedDict):
    assunto: str # entrada do usuario
    noticia_bruta: str # saida do buscador_noticia_bruta
    titulo: str # saida do resumidor
    resumo: str # saida do resumidor
    feedback: Literal["positivo", "negativo"] # saida do revisor
    tentativas: int # contador anti-loop
    approved: bool # deciçao humana
    messages: Annotated[list, add_messages] # se usar react tools
