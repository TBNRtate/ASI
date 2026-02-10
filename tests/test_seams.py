import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAIN_DIR = ROOT / "src/asi/brain"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
    return modules


def test_brain_never_imports_forbidden_modules() -> None:
    forbidden_exact = {
        "asi.llm.llama_cpp_backend",
        "llama_cpp",
        "transformers",
    }
    for py_file in BRAIN_DIR.rglob("*.py"):
        modules = _imported_modules(py_file)
        assert forbidden_exact.isdisjoint(modules), f"Forbidden import in {py_file}: {modules}"
        assert all(not module.startswith("asi.training") for module in modules), (
            f"Training import in brain module {py_file}: {modules}"
        )
