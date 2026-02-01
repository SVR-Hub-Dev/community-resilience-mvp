import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("python-mcp")


# ─────────────────────────────────────────────
# TOOL: analyze_file
# ─────────────────────────────────────────────
@mcp.tool()
def analyze_file(path: str) -> str:
    """Return the contents of a Python file."""
    p = Path(path)
    if not p.exists():
        return f"File not found: {path}"
    return p.read_text()


# ─────────────────────────────────────────────
# TOOL: generate_model
# ─────────────────────────────────────────────
@mcp.tool()
def generate_model(json_input: str) -> str:
    """Generate a Pydantic model from a JSON sample."""
    try:
        data = json.loads(json_input)
    except Exception as e:
        return f"Invalid JSON: {e}"

    fields = []
    for key, value in data.items():
        py_type = type(value).__name__
        fields.append(f"    {key}: {py_type}")

    model = (
        "from pydantic import BaseModel\n\n"
        "class GeneratedModel(BaseModel):\n" + "\n".join(fields)
    )
    return model


# ─────────────────────────────────────────────
# TOOL: explain_error
# ─────────────────────────────────────────────
@mcp.tool()
def explain_error(traceback_text: str) -> str:
    """Return a simple explanation of a Python traceback."""
    return f"Traceback received:\n\n{traceback_text}"


# ─────────────────────────────────────────────
# MAIN ENTRYPOINT
# ─────────────────────────────────────────────
def main():
    mcp.run()
