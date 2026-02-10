from __future__ import annotations

from pathlib import Path

from asi.brain.arabella_brain import ArabellaBrain
from asi.observability.ids import new_run_id


def main() -> None:
    brain = ArabellaBrain(config_dir=Path("configs"))
    print("ASI CLI. Type 'exit' to quit.")
    while True:
        user_input = input("you> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        run_id = new_run_id()
        response = brain.respond(user_input, session_id="cli", run_id=run_id)
        print(f"asi[{run_id}]> {response}")


if __name__ == "__main__":
    main()
