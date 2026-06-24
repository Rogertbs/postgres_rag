from langchain.tools import tool
from langchain.chat_models import init_chat_model

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

# 1 Definição das tools 

model = init_chat_model(
    "qwen2.5:1.5b",
    model_provider="ollama",
    base_url="http://172.16.200.20:11434",
    temperature=0,
)

# Define tools
@tool
def multiply(a: int, b: int) -> int:
    """Multiplies two numbers."""
    return a * b

@tool
def add(a: int, b: int) -> int:
    """Adds two numbers."""
    return a + b

@tool
def divide(a: int, b: int) -> float:
    """Divides two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b

tools = [add, multiply, divide]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)

# 2 Definição do estado

from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
import operator

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


# 3 Definição do nó

from langchain.messages import SystemMessage

def llm_call(state: dict):
    """LLM decides whether to call a tool or not"""

    return {
        "messages": [
            model_with_tools.invoke(
                [
                    SystemMessage(
                        content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
                    )
                ]
                + state["messages"]
            )
        ],
        "llm_calls": state.get('llm_calls', 0) + 1
    }


# 4 Defina o nó da ferramenta

#from langchain.messages import ToolMessage
from langchain_core.messages import ToolMessage

def tool_node(state: dict):
    """Performs the toll call"""

    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}

# 5. Defina a lógica final. função condicional

from typing import Literal
from langgraph.graph import StateGraph, START, END

def should_continute(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "tool_node"
    
    # Otherwise, we stop (reply to the user)
    return END

# 6. Construir e compilar o agente
# Build workflow

agent_builder = StateGraph(MessagesState)

# Add nodes
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)

# Add edges to connect nodes
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continute,
    ["tool_node", END]
)
agent_builder.add_edge("tool_node", "llm_call")

# Create Checkpointer
checkpointer = InMemorySaver()

# Compile the agent
agent = agent_builder.compile(checkpointer=checkpointer)
#agent = agent_builder.compile()

# Compile the agent
#from IPython.display import image, display
#display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

# Invoke
from langchain.messages import HumanMessage
# messages = [HumanMessage(content="Add 3 and 4.")]
# messages = agent.invoke({"messages": [HumanMessage(content="Add 3 and 4.")]}, {"configurable": {"thread_id": "thread-1"}})
# for m in messages["messages"]:
#     m.pretty_print()

if __name__ == "__main__":

    CONFIG = {"configurable": {"thread_id": "thread-1"}}

    def mostrar_estado(label):
        snap = agent.get_state(CONFIG)
        print(f"\n=== {label} ===")
        print(f"  proximo nao: {snap.next}")
        print(f"  total de mensagens no state: {len(snap.values.get('messages', []))}")
        print(f"  llm_calls: {snap.values.get('llm_calls', 0)}")

    # --- 1ª rodada: pergunta nova ---
    print("\n" + "="*60)
    print(" RODADA 1 é pergunta nova (Add 3 and 4)")
    print("="*60)
    agent.invoke({"messages": [HumanMessage(content="Add 3 and 4.")]}, CONFIG)
    mostrar_estado("apos rodada 1")
    for m in agent.get_state(CONFIG).values["messages"]:
        m.pretty_print()

    # --- 2ª rodada: MESMO thread_id, continua a conversa ---
    print("\n" + "="*60)
    print(" RODADA 2 continua (agora some com 5)")
    print("="*60)
    agent.invoke({"messages": [HumanMessage(content="Now multiply the result by 5.")]}, CONFIG)
    mostrar_estado("apos rodada 2")
    for m in agent.get_state(CONFIG).values["messages"]:
        m.pretty_print()

    # --- 3ª rodada: thread_id DIFERENTE é conversa isolada ---
    print("\n" + "="*60)
    print(" RODADA 3 é thread_id novo (conversa separada)")
    print("="*60)
    CONFIG2 = {"configurable": {"thread_id": "thread-2"}}
    agent.invoke({"messages": [HumanMessage(content="Add 100 and 200.")]}, CONFIG2)
    mostrar_estado("apos rodada 3 (thread-2)")
    for m in agent.get_state(CONFIG2).values["messages"]:
        m.pretty_print()

    # --- prova de isolamento: volta pra thread-1 ---
    print("\n" + "="*60)
    print(" VOLTANDO em thread-1 e a memoria estao intacta?")
    print("="*60)
    mostrar_estado("thread-1 (sem nova invoke)")

