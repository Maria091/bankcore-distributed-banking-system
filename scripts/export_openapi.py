"""Export the current FastAPI schema to docs/openapi.json for API review."""
import json
from pathlib import Path
from bankcore.api import app

output = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Exported OpenAPI specification to {output}")
