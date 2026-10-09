"""The committed web/openapi.json and web/src/lib/api-types.ts must match the server.

If this fails, regenerate:
  cd server && uv run python -c "import json; from app.main import create_app; \
      print(json.dumps(create_app().openapi()))" > ../web/openapi.json
  cd ../web && npm run gen:types
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.main import create_app

WEB = Path(__file__).parent.parent.parent / "web"


def test_committed_openapi_matches_server():
    committed = json.loads((WEB / "openapi.json").read_text())
    assert committed == json.loads(json.dumps(create_app().openapi())), \
        "web/openapi.json is stale: regenerate it (see this file's docstring)"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_committed_types_match_openapi(tmp_path):
    work = tmp_path / "web"
    (work / "scripts").mkdir(parents=True)
    (work / "src/lib").mkdir(parents=True)
    shutil.copy(WEB / "openapi.json", work / "openapi.json")
    shutil.copy(WEB / "scripts/gen-types.mjs", work / "scripts/gen-types.mjs")
    subprocess.run(["node", "scripts/gen-types.mjs"], cwd=work, check=True, capture_output=True)
    assert (work / "src/lib/api-types.ts").read_text() == (WEB / "src/lib/api-types.ts").read_text(), \
        "web/src/lib/api-types.ts is stale: run `npm run gen:types`"
