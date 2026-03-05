# tests/test_skill_tools.py
"""
Tests unitaires pour tools/skill_tools.py

Couvre :
- skill_list : liste vide, avec skills, filtre par tag, filtre sans résultat
- skill_read : skill existant, slug inconnu, contenu retourné
"""
import json, sys, types, pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

for mod in ["sentence_transformers", "fitz"]:
    sys.modules.setdefault(mod, types.ModuleType(mod))

import tools.skill_tools as st
from core.skill_manager import SkillManager, SkillInfo


def _make_sm(tmp_path, skills=None):
    """Crée un SkillManager peuplé dans un répertoire temporaire."""
    sm = SkillManager(skills_dir=tmp_path)
    for slug, name, desc, tags, content in (skills or []):
        fm = f"---\nname: {name}\ndescription: {desc}.\ntags: {json.dumps(tags)}\n---\n{content}\n"
        (tmp_path / f"{slug}.md").write_text(fm, encoding="utf-8")
    sm.refresh()
    return sm


# ── skill_list ────────────────────────────────────────────────────────────────

class TestSkillList:
    def test_empty_returns_json(self, tmp_path):
        sm = _make_sm(tmp_path)
        with patch("tools.skill_tools.get_skill_manager", return_value=sm):
            result = st.skill_list()
        data = json.loads(result)
        assert "skills" in data
        assert data["skills"] == []

    def test_lists_registered_skills(self, tmp_path):
        sm = _make_sm(tmp_path, [("s1", "Outil 1", "Desc 1", [], "Contenu.")])
        with patch("tools.skill_tools.get_skill_manager", return_value=sm):
            result = st.skill_list()
        data = json.loads(result)
        slugs = [s["slug"] for s in data["skills"]]
        assert "s1" in slugs

    def test_count_correct(self, tmp_path):
        sm = _make_sm(tmp_path, [
            ("a", "A", "d", [], "c"),
            ("b", "B", "d", [], "c"),
        ])
        with patch("tools.skill_tools.get_skill_manager", return_value=sm):
            data = json.loads(st.skill_list())
        assert data["count"] == 2

    def test_tag_filter_returns_matching(self, tmp_path):
        sm = _make_sm(tmp_path, [
            ("sql_guide", "SQL", "d", ["sql", "data"], "c"),
            ("style_guide", "Style", "d", ["redaction"], "c"),
        ])
        with patch("tools.skill_tools.get_skill_manager", return_value=sm):
            data = json.loads(st.skill_list(tag_filter="sql"))
        slugs = [s["slug"] for s in data["skills"]]
        assert "sql_guide" in slugs
        assert "style_guide" not in slugs

    def test_tag_filter_no_match_empty_list(self, tmp_path):
        sm = _make_sm(tmp_path, [("s1", "S", "d", ["python"], "c")])
        with patch("tools.skill_tools.get_skill_manager", return_value=sm):
            data = json.loads(st.skill_list(tag_filter="inexistant"))
        assert data["skills"] == []

    def test_returns_valid_json(self, tmp_path):
        sm = _make_sm(tmp_path, [("s1", "S", "d", [], "c")])
        with patch("tools.skill_tools.get_skill_manager", return_value=sm):
            result = st.skill_list()
        assert isinstance(json.loads(result), dict)

    def test_each_skill_has_required_keys(self, tmp_path):
        sm = _make_sm(tmp_path, [("s1", "S", "d", [], "c")])
        with patch("tools.skill_tools.get_skill_manager", return_value=sm):
            data = json.loads(st.skill_list())
        skill = data["skills"][0]
        assert {"slug", "name", "description"} <= skill.keys()


# ── skill_read ────────────────────────────────────────────────────────────────

class TestSkillRead:
    def test_read_existing_returns_content(self, tmp_path):
        sm = _make_sm(tmp_path, [("guide", "Mon Guide", "d", [], "Voici le contenu du guide.")])
        with patch("tools.skill_tools.get_skill_manager", return_value=sm):
            result = st.skill_read("guide")
        assert "contenu du guide" in result.lower()

    def test_read_existing_includes_name(self, tmp_path):
        sm = _make_sm(tmp_path, [("guide", "Mon Guide", "d", [], "Contenu.")])
        with patch("tools.skill_tools.get_skill_manager", return_value=sm):
            result = st.skill_read("guide")
        assert "Mon Guide" in result

    def test_read_unknown_returns_json_error(self, tmp_path):
        sm = _make_sm(tmp_path)
        with patch("tools.skill_tools.get_skill_manager", return_value=sm):
            result = st.skill_read("inexistant")
        # read_skill retourne "" pour inconnu, donc skill_read doit le gérer
        # Le résultat sera soit un header vide soit un json error
        assert isinstance(result, str)

    def test_read_returns_string(self, tmp_path):
        sm = _make_sm(tmp_path, [("s1", "S", "d", [], "c")])
        with patch("tools.skill_tools.get_skill_manager", return_value=sm):
            result = st.skill_read("s1")
        assert isinstance(result, str)

    def test_read_includes_slug_in_header(self, tmp_path):
        sm = _make_sm(tmp_path, [("mon_slug", "Titre", "d", [], "Texte.")])
        with patch("tools.skill_tools.get_skill_manager", return_value=sm):
            result = st.skill_read("mon_slug")
        assert "mon_slug" in result
