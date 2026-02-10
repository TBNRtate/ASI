from __future__ import annotations

from pathlib import Path

from asi.brain.arabella_brain import ArabellaBrain


def main() -> None:
    brain = ArabellaBrain(config_dir=Path("configs"))
    print("ASI CLI. Type 'exit' to quit.")
    while True:
        user_input = input("you> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        response = brain.respond(user_input, session_id="cli")
        print(f"asi> {response}")


if __name__ == "__main__":
    main()
