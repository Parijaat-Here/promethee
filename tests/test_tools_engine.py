# tests/test_tools_engine.py
"""
Tests unitaires pour core/tools_engine.py

Couvre :
- Décorateur @tool : enregistrement, schéma, famille
- call_tool : appel nominal, outil inconnu, erreur runtime
- disable/enable_family, is_family_disabled
- get_tool_schemas : filtre les familles désactivées
- list_tools, registered_tool_names
- apply_profile_families
- list_families
"""
import pytest
from unittest.mock import patch
import core.tools_engine as te


@pytest.fixture(autouse=True)
def clean_registry():
    """Isole chaque test : sauvegarde et restaure l'état global du registre."""
    saved_tools    = dict(te._TOOLS)
    saved_disabled = set(te._DISABLED_FAMILIES)
    saved_family   = te._current_family
    saved_label    = te._current_family_label
    saved_icon     = te._current_family_icon
    yield
    te._TOOLS.clear()
    te._TOOLS.update(saved_tools)
    te._DISABLED_FAMILIES.clear()
    te._DISABLED_FAMILIES.update(saved_disabled)
    te._current_family      = saved_family
    te._current_family_label = saved_label
    te._current_family_icon  = saved_icon


def _register_tool(name="test_tool", family="test_family", fn=None):
    """Helper : enregistre un outil minimal pour les tests."""
    te.set_current_family(family, family.replace("_", " ").title(), "🔧")
    if fn is None:
        fn = lambda x: f"result:{x}"
    decorated = te.tool(
        name=name,
        description=f"Description de {name}",
        parameters={"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]},
    )(fn)
    return decorated


# ── @tool decorator ───────────────────────────────────────────────────────────

class TestToolDecorator:
    def test_registers_tool(self):
        _register_tool("t1")
        assert "t1" in te._TOOLS

    def test_schema_has_name(self):
        _register_tool("t2")
        assert te._TOOLS["t2"]["schema"]["function"]["name"] == "t2"

    def test_schema_has_description(self):
        _register_tool("t3")
        assert "Description de t3" in te._TOOLS["t3"]["schema"]["function"]["description"]

    def test_family_stored(self):
        _register_tool("t4", family="ma_famille")
        assert te._TOOLS["t4"]["family"] == "ma_famille"

    def test_decorated_function_still_callable(self):
        fn = _register_tool("t5")
        assert fn(x="hello") == "result:hello"

    def test_overwrite_existing_tool(self):
        _register_tool("t6", fn=lambda x: "v1")
        _register_tool("t6", fn=lambda x: "v2")
        assert te._TOOLS["t6"]["fn"](x="") == "v2"


# ── call_tool ─────────────────────────────────────────────────────────────────

class TestCallTool:
    def test_calls_registered_tool(self):
        _register_tool("ct1", fn=lambda x: f"ok:{x}")
        result = te.call_tool("ct1", {"x": "test"})
        assert "ok:test" in result

    def test_unknown_tool_returns_error_string(self):
        result = te.call_tool("outil_inexistant", {})
        assert "inconnu" in result.lower() or "outil_inexistant" in result

    def test_runtime_error_returns_string(self):
        _register_tool("ct2", fn=lambda x: 1 / 0)
        result = te.call_tool("ct2", {"x": "test"})
        assert isinstance(result, str)
        assert "ct2" in result or "erreur" in result.lower()

    def test_dict_result_serialized_to_json(self):
        _register_tool("ct3", fn=lambda x: {"key": "value"})
        result = te.call_tool("ct3", {"x": ""})
        assert '"key"' in result

    def test_list_result_serialized_to_json(self):
        _register_tool("ct4", fn=lambda x: [1, 2, 3])
        result = te.call_tool("ct4", {"x": ""})
        assert "1" in result and "2" in result

    def test_string_result_returned_as_is(self):
        _register_tool("ct5", fn=lambda x: "bonjour")
        assert te.call_tool("ct5", {"x": ""}) == "bonjour"


# ── disable / enable family ───────────────────────────────────────────────────

class TestFamilyControl:
    def test_disable_family(self):
        te.disable_family("fam_x")
        assert te.is_family_disabled("fam_x") is True

    def test_enable_family(self):
        te.disable_family("fam_y")
        te.enable_family("fam_y")
        assert te.is_family_disabled("fam_y") is False

    def test_unknown_family_not_disabled(self):
        assert te.is_family_disabled("famille_inconnue") is False

    def test_get_tool_schemas_excludes_disabled(self):
        _register_tool("s1", family="active_fam")
        _register_tool("s2", family="disabled_fam")
        te.disable_family("disabled_fam")
        schemas = te.get_tool_schemas()
        names = [s["function"]["name"] for s in schemas]
        assert "s1" in names
        assert "s2" not in names

    def test_get_tool_schemas_includes_enabled(self):
        _register_tool("s3", family="enabled_fam")
        schemas = te.get_tool_schemas()
        names = [s["function"]["name"] for s in schemas]
        assert "s3" in names

    def test_apply_profile_disables(self):
        _register_tool("ap1", family="fam_to_disable")
        te.apply_profile_families(enabled=[], disabled=["fam_to_disable"])
        assert te.is_family_disabled("fam_to_disable")

    def test_apply_profile_enables(self):
        te.disable_family("fam_to_enable")
        te.apply_profile_families(enabled=["fam_to_enable"], disabled=[])
        assert not te.is_family_disabled("fam_to_enable")

    def test_apply_profile_empty_restores(self):
        te.disable_family("fam_restore")
        with patch.object(te, "_load_disabled_families"):
            te.apply_profile_families(enabled=[], disabled=[])
        # La fonction doit appeler _load_disabled_families (pas lever d'erreur)


# ── list_tools / registered_tool_names ────────────────────────────────────────

class TestListTools:
    def test_registered_tool_names_contains_registered(self):
        _register_tool("ln1")
        assert "ln1" in te.registered_tool_names()

    def test_list_tools_returns_list(self):
        assert isinstance(te.list_tools(), list)

    def test_list_tools_entry_has_required_keys(self):
        _register_tool("lt1")
        entry = next(t for t in te.list_tools() if t["name"] == "lt1")
        assert {"name", "description", "family", "enabled"} <= entry.keys()

    def test_list_families_returns_list(self):
        _register_tool("lf1", family="fam_list")
        families = te.list_families()
        assert isinstance(families, list)

    def test_list_families_entry_has_required_keys(self):
        _register_tool("lf2", family="fam_detail")
        families = te.list_families()
        fam = next((f for f in families if f["family"] == "fam_detail"), None)
        assert fam is not None
        assert {"family", "label", "enabled", "tool_count"} <= fam.keys()

    def test_disabled_family_reflected_in_list_tools(self):
        _register_tool("lt2", family="dis_fam")
        te.disable_family("dis_fam")
        entry = next(t for t in te.list_tools() if t["name"] == "lt2")
        assert entry["enabled"] is False
