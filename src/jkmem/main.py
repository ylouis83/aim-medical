from jkmem.agent import MemoryAgent
from jkmem.llm import call_llm
from jkmem.memory_backends import get_memory_backend


def main() -> None:
    memory = get_memory_backend()
    agent = MemoryAgent(memory=memory, llm_fn=call_llm)

    print("JKMem agent is running. Type 'exit' to quit.")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
        response = agent.respond(user_input)
        print(f"Agent: {response}")


if __name__ == "__main__":
    main()
