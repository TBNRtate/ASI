# ASI Agent Guardrails

Architectural non-negotiables for this repository:

1. **Brain import boundary**
   - `src/asi/brain/` must not import backend implementations directly.
   - Brain may import interfaces and factories only (e.g. `asi.llm.factory`).

2. **Sandbox safety**
   - Never use `shell=True` in subprocess execution.

3. **Structured tool calling**
   - Tool invocation must use structured payloads (e.g., JSON/object schema), not regex parsing.

4. **Training quarantine**
   - Training code must live under `src/asi/training/` and must never be imported by runtime paths.
