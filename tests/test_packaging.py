"""Packaging tests for Claude plugin, MCP registry manifest, and repo files."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_plugin_json_structure_and_keys():
    plugin_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
    assert plugin_path.exists(), "plugin.json must exist"

    data = json.loads(plugin_path.read_text(encoding="utf-8"))
    required_keys = {
        "name",
        "description",
        "version",
        "author",
        "license",
        "keywords",
        "mcpServers",
    }
    for key in required_keys:
        assert key in data, f"plugin.json missing required key: {key}"

    assert data["name"] == "as-ig-mcp"
    assert isinstance(data["keywords"], list) and len(data["keywords"]) > 0


def test_plugin_mcp_servers_launcher_pinned_version():
    plugin_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_path.read_text(encoding="utf-8"))
    mcp_servers = data.get("mcpServers", {})
    assert "as-ig" in mcp_servers, "mcpServers must contain 'as-ig'"

    server_conf = mcp_servers["as-ig"]
    args = server_conf.get("args", [])
    # Check that launcher pins an exact version (contains '==') to prevent unpinned launcher blocks
    has_pinned_version = any("==" in str(arg) for arg in args)
    assert has_pinned_version, "Launcher args must pin an exact version with '=='"


def test_marketplace_json_entry_matches_plugin():
    marketplace_path = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    assert marketplace_path.exists(), "marketplace.json must exist"

    market_data = json.loads(marketplace_path.read_text(encoding="utf-8"))
    plugin_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
    plugin_data = json.loads(plugin_path.read_text(encoding="utf-8"))

    plugins = market_data.get("plugins", [])
    assert len(plugins) > 0, "marketplace.json must contain at least one plugin"
    assert any(
        p.get("name") == plugin_data["name"] for p in plugins
    ), f"marketplace.json plugin name must match {plugin_data['name']}"


def test_server_json_registry_manifest():
    server_path = REPO_ROOT / "server.json"
    assert server_path.exists(), "server.json must exist"

    server_data = json.loads(server_path.read_text(encoding="utf-8"))
    assert server_data["name"].startswith(
        "io.github."
    ), "server.json name must start with io.github."

    packages = server_data.get("packages", [])
    assert len(packages) > 0, "server.json must declare at least one package"

    pyproject_path = REPO_ROOT / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    project_name = pyproject_data["project"]["name"]
    project_version = pyproject_data["project"]["version"]

    pypi_package = packages[0]
    assert (
        pypi_package.get("identifier") == project_name
    ), f"Package identifier {pypi_package.get('identifier')} must match pyproject name {project_name}"
    assert (
        server_data.get("version") == project_version
    ), f"server.json version must match pyproject.toml version {project_version}"
    assert (
        pypi_package.get("version") == project_version
    ), f"package version must match pyproject.toml version {project_version}"


def test_readme_contains_mcp_name_marker():
    readme_path = REPO_ROOT / "README.md"
    assert readme_path.exists(), "README.md must exist"

    content = readme_path.read_text(encoding="utf-8")
    assert "<!-- mcp-name: io.github.aswathas/as-ig-mcp -->" in content


def test_pyproject_and_license_exist_and_non_empty():
    pyproject_path = REPO_ROOT / "pyproject.toml"
    license_path = REPO_ROOT / "LICENSE"

    assert pyproject_path.exists(), "pyproject.toml must exist"
    assert pyproject_path.stat().st_size > 0, "pyproject.toml must not be empty"

    assert license_path.exists(), "LICENSE must exist"
    assert license_path.stat().st_size > 0, "LICENSE must not be empty"

    license_content = license_path.read_text(encoding="utf-8")
    assert "Copyright (c) 2026 Aswath" in license_content
