# tests/test_session_memory.py
import json, pytest
from unittest.mock import MagicMock
from core.session_memory import SessionMemory, _ToolRecord

def _mem(**kw):
    return SessionMemory(MagicMock(), model="test", **kw)

def _amsg(content="", tool_calls=None):
    m = {"role": "assistant", "content": content}
    if tool_calls: m["tool_calls"] = tool_calls
    return m

def _tmsg(tc_id, content="res"):
    return {"role": "tool", "tool_call_id": tc_id, "content": content}

def _tc(tc_id, name):
    return {"id": tc_id, "function": {"name": name}}

class TestIsCode:
    def test_python_def(self):
        assert SessionMemory._is_code("def foo():\n    return 42")
    def test_python_class(self):
        assert SessionMemory._is_code("class M:\n    pass")
    def test_python_import(self):
        assert SessionMemory._is_code("import os")
    def test_sql_select(self):
        assert SessionMemory._is_code("SELECT id FROM users WHERE active = 1")
    def test_js_const(self):
        assert SessionMemory._is_code("const x = 42;")
    def test_weak_markers(self):
        assert SessionMemory._is_code("return value\nraise ValueError\nprint(x)")
    def test_plain_text(self):
        assert not SessionMemory._is_code("Bonjour voici le resume de la reunion.")
    def test_empty(self):
        assert not SessionMemory._is_code("")

class TestHasImage:
    def test_true(self):
        assert SessionMemory._has_image(json.dumps({"image_generated": True}))
    def test_false_value(self):
        assert not SessionMemory._has_image(json.dumps({"image_generated": False}))
    def test_no_key(self):
        assert not SessionMemory._has_image(json.dumps({"status": "ok"}))
    def test_invalid_json(self):
        assert not SessionMemory._has_image('{"image_generated": true, oups}')
    def test_plain(self):
        assert not SessionMemory._has_image("rien ici")

class TestIsCited:
    def test_name_and_snippet(self):
        r = "Les horaires souples permettent une meilleure organisation du travail."
        a = "search_web indique que les horaires souples permettent une meilleure organisation du travail."
        assert SessionMemory._is_cited("search_web", r, a)
    def test_significant_number(self):
        assert SessionMemory._is_cited("get_stats", "Resultat : 12345 enregistrements.", "get_stats a retourne 12345 resultats.")
    def test_no_match(self):
        assert not SessionMemory._is_cited("tool", "contenu X", "reponse sans rapport")

class TestRecord:
    def test_image_pinned(self):
        m = _mem()
        m.record_tool_result("t", json.dumps({"image_generated": True}), "", turn=0)
        assert m._records[0].pinned is True
    def test_code_pinned(self):
        m = _mem()
        m.record_tool_result("t", "def foo():\n    return 42", "", turn=0)
        assert m._records[0].pinned is True
    def test_pending_without_text(self):
        m = _mem()
        m.record_tool_result("t", "Texte normal.", "", turn=0)
        assert len(m._pending_records) == 1
    def test_pinning_disabled(self):
        m = _mem(pinning_enabled=False)
        m.record_tool_result("t", "def f(): pass", "", turn=0)
        assert m._records[0].pinned is False

class TestFlushPending:
    def test_evaluates_with_text(self):
        m = _mem()
        r = "Les resultats montrent que 12345 documents ont ete traites."
        m._pending_records.append(_ToolRecord(0, "search_docs", r, len(r), False))
        m.flush_pending([_amsg("search_docs a trouve 12345 documents.")])
        assert m._records[0].pinned is True
    def test_empty_noop(self):
        m = _mem()
        m.flush_pending([])
        assert m._records == []

class TestProtection:
    def test_pinned_gets_marker(self):
        m = _mem()
        m._records.append(_ToolRecord(0, "python_exec", "code", 4, True))
        msgs = [_amsg(tool_calls=[_tc("c1","python_exec")]), _tmsg("c1","def f(): pass")]
        result = m.apply_pinned_protection(msgs)
        assert result[1].get("_pinned") is True

class TestStrip:
    def test_removes_private_keys(self):
        m = _mem()
        msgs = [{"role": "system", "content": "x", "_is_consolidation": True}]
        clean = m.strip_internal_markers(msgs)
        assert "_is_consolidation" not in clean[0]

class TestConsolidate:
    def _stream(self, text):
        return iter([MagicMock(choices=[MagicMock(delta=MagicMock(content=text))], usage=None),
                     MagicMock(choices=[], usage=None)])
    def _msgs(self):
        return [{"role": "system", "content": "sys"}, {"role": "user", "content": "q"},
                {"role": "assistant", "content": "a"}]
    def test_no_action_at_turn_0(self):
        m = _mem(consolidation_every=2)
        msgs = self._msgs()
        assert m.maybe_consolidate(msgs, current_turn=0) is msgs
    def test_consolidation_triggered(self):
        m = _mem(consolidation_every=2)
        m._client.chat.completions.create.return_value = self._stream("Resume test")
        result = m.maybe_consolidate(self._msgs(), current_turn=2)
        cons = [x for x in result if x.get("_is_consolidation")]
        assert len(cons) == 1 and "Resume test" in cons[0]["content"]
    def test_cursor_advances_on_empty(self):
        m = _mem(consolidation_every=2)
        m._client.chat.completions.create.return_value = self._stream("")
        m.maybe_consolidate(self._msgs(), current_turn=2)
        assert m._last_consolidated_at == 2


# ── Compléments : méthodes non couvertes ──────────────────────────────────────

class TestApplyPinnedProtection:
    def test_no_pinning_returns_msgs_unchanged(self):
        mem = _mem(pinning_enabled=False)
        msgs = [{"role": "user", "content": "x"}]
        result = mem.apply_pinned_protection(msgs)
        assert result == msgs

    def test_pinning_enabled_no_pinned_records_unchanged(self):
        mem = _mem(pinning_enabled=True)
        msgs = [{"role": "user", "content": "x"}]
        result = mem.apply_pinned_protection(msgs)
        assert result == msgs

    def test_returns_list(self):
        mem = _mem()
        result = mem.apply_pinned_protection([])
        assert isinstance(result, list)

    def test_non_tool_msgs_untouched(self):
        mem = _mem(pinning_enabled=True)
        msgs = [{"role": "assistant", "content": "hello"}]
        result = mem.apply_pinned_protection(msgs)
        assert result[0].get("_pinned") is None


class TestStripInternalMarkers:
    def test_removes_pinned_marker(self):
        mem = _mem()
        msgs = [{"role": "tool", "content": "x", "_pinned": True}]
        result = mem.strip_internal_markers(msgs)
        assert "_pinned" not in result[0]

    def test_removes_consolidation_marker(self):
        mem = _mem()
        msgs = [{"role": "assistant", "content": "x", "_is_consolidation": True}]
        result = mem.strip_internal_markers(msgs)
        assert "_is_consolidation" not in result[0]

    def test_preserves_regular_keys(self):
        mem = _mem()
        msgs = [{"role": "user", "content": "bonjour", "_private": True}]
        result = mem.strip_internal_markers(msgs)
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "bonjour"

    def test_empty_list(self):
        mem = _mem()
        assert mem.strip_internal_markers([]) == []

    def test_no_markers_unchanged(self):
        mem = _mem()
        msgs = [{"role": "user", "content": "clean"}]
        result = mem.strip_internal_markers(msgs)
        assert result[0] == {"role": "user", "content": "clean"}


class TestProperties:
    def test_last_summary_initially_none(self):
        mem = _mem()
        assert mem.last_summary is None

    def test_pinned_tool_names_initially_empty(self):
        mem = _mem()
        assert mem.pinned_tool_names == set()

    def test_pinned_tool_names_type(self):
        mem = _mem()
        assert isinstance(mem.pinned_tool_names, set)
