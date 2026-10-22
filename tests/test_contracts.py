import ast
from pathlib import Path

def test_bundled_plugins_are_valid_python():
    root = Path(__file__).resolve().parents[1]
    files = list((root / "plugins").glob("*/plugin.py"))
    assert files
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"))

def test_env_example_does_not_contain_real_secrets():
    content = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")
    assert "TELEGRAM_BOT_TOKEN=" in content and "PLAYEROK_TOKEN=" in content
    assert "replace-with-a-random-secret" in content
