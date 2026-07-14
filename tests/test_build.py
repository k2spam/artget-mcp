"""The plugin build produces a valid bundle (manifest + mcp config + skill)."""
import importlib.util
import json
import os
import zipfile

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "bp", os.path.join(_HERE, "scripts", "build_plugin.py"))
bp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bp)


def test_manifest_and_mcp_valid_json():
    m = json.load(open(os.path.join(_HERE, "plugin/.claude-plugin/plugin.json")))
    assert m["name"] == "heroquarium-artgen"
    assert m["version"].count(".") == 2
    mcp = json.load(open(os.path.join(_HERE, "plugin/.mcp.json")))
    assert "heroquarium-artgen" in mcp["mcpServers"]


def test_build_bundle_contents(tmp_path, monkeypatch):
    monkeypatch.setattr(bp, "BUILD", str(tmp_path))
    out, n = bp.build(bp.read_version())
    assert os.path.exists(out) and n > 10
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
    for required in (".claude-plugin/plugin.json", ".mcp.json",
                     "skills/heroquarium-artgen/SKILL.md", "mcp/server.py",
                     "palette.json", "artgen/iso.py", "artgen/iso_actors.py"):
        assert required in names, required
    assert not any("__pycache__" in n for n in names)


def test_bump():
    assert bp.bump("0.1.0", "patch") == "0.1.1"
    assert bp.bump("0.1.9", "minor") == "0.2.0"
    assert bp.bump("1.4.2", "major") == "2.0.0"
