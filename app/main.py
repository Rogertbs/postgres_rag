from agent_reporter.agent import agent
from langchain_core.messages import HumanMessage
from langgraph.types import Command

config = {"configurable": {"thread_id": "thread-1"}}

for chunk in agent.stream({"assunto": "inteligencia artificial"}, config=config):
    print(chunk)

# Loop de aprovacao
while True:
    snap = agent.get_state(config)
    if not snap.next: # grafo terminou (END)
        break

    decisao = input("\nAprovar? [s/n]: ").strip()
    result = agent.invoke(Command(update={"approved": decisao == "s"}), config=config)
    if decisao == "s":    
        for m in result.get("messages", []):
            m.pretty_print()
        break