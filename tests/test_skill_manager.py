# tests/test_skill_manager.py
import pytest
from pathlib import Path
from core.skill_manager import SkillManager, SkillInfo

@pytest.fixture()
def sm(skills_dir):
    return SkillManager(skills_dir=skills_dir)

def _write(skills_dir, slug, content):
    (skills_dir / f"{slug}.md").write_text(content, encoding="utf-8")

VALID = "---\nname: Outil de test\ndescription: Une skill de test.\n---\nVoici le contenu.\n"
VALID_TAGS = "---\nname: Avec Tags\ndescription: d.\ntags: [python, data]\nversion: 2.1\n---\nContenu.\n"
NO_FM = "# Titre\nPremière ligne de contenu."


# ── SkillInfo ─────────────────────────────────────────────────────────────────

class TestSkillInfo:
    def test_to_dict_keys(self, sm, skills_dir):
        _write(skills_dir, "s1", VALID)
        sm.refresh()
        d = sm.get_info("s1").to_dict()
        assert {"slug", "name", "description", "tags", "version", "size_chars"} <= d.keys()

    def test_to_dict_slug(self, sm, skills_dir):
        _write(skills_dir, "mon_outil", VALID)
        sm.refresh()
        assert sm.get_info("mon_outil").to_dict()["slug"] == "mon_outil"


# ── list_skills ───────────────────────────────────────────────────────────────

class TestList:
    def test_empty(self, sm):
        assert sm.list_skills() == []

    def test_lists_skill(self, sm, skills_dir):
        _write(skills_dir, "s1", VALID)
        sm.refresh()
        assert any(s.slug == "s1" for s in sm.list_skills())

    def test_name_from_frontmatter(self, sm, skills_dir):
        _write(skills_dir, "s1", VALID)
        sm.refresh()
        assert sm.get_info("s1").name == "Outil de test"

    def test_description_from_frontmatter(self, sm, skills_dir):
        _write(skills_dir, "s1", VALID)
        sm.refresh()
        assert "skill de test" in sm.get_info("s1").description.lower()

    def test_tags_from_frontmatter(self, sm, skills_dir):
        _write(skills_dir, "t", VALID_TAGS)
        sm.refresh()
        assert sm.get_info("t").tags == ["python", "data"]

    def test_version_from_frontmatter(self, sm, skills_dir):
        _write(skills_dir, "t", VALID_TAGS)
        sm.refresh()
        assert sm.get_info("t").version == "2.1"

    def test_name_fallback_no_frontmatter(self, sm, skills_dir):
        _write(skills_dir, "mon_outil", NO_FM)
        sm.refresh()
        info = sm.get_info("mon_outil")
        assert info.name  # non vide

    def test_description_fallback_body(self, sm, skills_dir):
        _write(skills_dir, "nofm", NO_FM)
        sm.refresh()
        info = sm.get_info("nofm")
        assert info.description  # déduite de la première ligne

    def test_multiple_skills(self, sm, skills_dir):
        _write(skills_dir, "a", VALID)
        _write(skills_dir, "b", VALID)
        sm.refresh()
        slugs = [s.slug for s in sm.list_skills()]
        assert "a" in slugs and "b" in slugs

    def test_returns_list_type(self, sm):
        assert isinstance(sm.list_skills(), list)


# ── exists / get_info ─────────────────────────────────────────────────────────

class TestExistsRead:
    def test_exists_true(self, sm, skills_dir):
        _write(skills_dir, "existe", VALID)
        sm.refresh()
        assert sm.exists("existe") is True

    def test_exists_false(self, sm):
        assert sm.exists("nexiste_pas") is False

    def test_get_info_returns_skillinfo(self, sm, skills_dir):
        _write(skills_dir, "s", VALID)
        sm.refresh()
        assert isinstance(sm.get_info("s"), SkillInfo)

    def test_get_info_unknown_returns_none(self, sm):
        assert sm.get_info("inconnu") is None

    def test_read_returns_content(self, sm, skills_dir):
        _write(skills_dir, "r", VALID)
        sm.refresh()
        assert "contenu" in sm.read_skill("r").lower()

    def test_read_unknown_returns_empty(self, sm):
        assert sm.read_skill("inexistant") == ""

    def test_read_max_chars_respected(self, sm, skills_dir):
        _write(skills_dir, "long", "---\nname: L\ndescription: d.\n---\n" + "x" * 10000)
        sm.refresh()
        assert len(sm.read_skill("long", max_chars=100)) <= 300  # +marge tronquage

    def test_read_short_not_truncated(self, sm, skills_dir):
        _write(skills_dir, "short", VALID)
        sm.refresh()
        content = sm.read_skill("short", max_chars=10000)
        assert "contenu" in content.lower()


# ── save_skill ────────────────────────────────────────────────────────────────

class TestSaveDelete:
    def test_save_creates_file(self, sm, skills_dir):
        sm.save_skill("new_s", "---\nname: N\ndescription: d.\n---\nC.")
        assert (skills_dir / "new_s.md").exists()

    def test_save_returns_skillinfo(self, sm):
        info = sm.save_skill("ret", VALID)
        assert isinstance(info, SkillInfo)
        assert info.slug == "ret"

    def test_save_updates_existing(self, sm, skills_dir):
        _write(skills_dir, "upd", VALID)
        sm.refresh()
        sm.save_skill("upd", "---\nname: Nouveau\ndescription: d.\n---\nMàJ.")
        sm.refresh()
        assert sm.get_info("upd").name == "Nouveau"

    def test_save_invalid_slug_raises(self, sm):
        with pytest.raises(ValueError):
            sm.save_skill("slug invalide!", VALID)

    def test_save_slug_with_dot_raises(self, sm):
        with pytest.raises(ValueError):
            sm.save_skill("slug.bad", VALID)

    def test_delete_removes(self, sm, skills_dir):
        _write(skills_dir, "del_me", VALID)
        sm.refresh()
        sm.delete_skill("del_me")
        sm.refresh()
        assert not sm.exists("del_me")

    def test_delete_removes_file(self, sm, skills_dir):
        _write(skills_dir, "del_file", VALID)
        sm.refresh()
        sm.delete_skill("del_file")
        assert not (skills_dir / "del_file.md").exists()

    def test_delete_unknown_no_raise(self, sm):
        sm.delete_skill("inexistant")  # ne doit pas lever d'exception

    def test_delete_then_not_exists(self, sm, skills_dir):
        _write(skills_dir, "gone", VALID)
        sm.refresh()
        sm.delete_skill("gone")
        assert not sm.exists("gone")


# ── build_pinned_block ────────────────────────────────────────────────────────

class TestPinnedBlock:
    def test_empty_list(self, sm):
        assert sm.build_pinned_block([]) == ""

    def test_contains_skill_name(self, sm, skills_dir):
        _write(skills_dir, "ps", VALID)
        sm.refresh()
        block = sm.build_pinned_block(["ps"])
        assert "Outil de test" in block

    def test_contains_skill_content(self, sm, skills_dir):
        _write(skills_dir, "ps", VALID)
        sm.refresh()
        block = sm.build_pinned_block(["ps"])
        assert "contenu" in block.lower()

    def test_returns_string(self, sm, skills_dir):
        _write(skills_dir, "ps", VALID)
        sm.refresh()
        assert isinstance(sm.build_pinned_block(["ps"]), str)

    def test_unknown_slug_ignored_no_raise(self, sm):
        block = sm.build_pinned_block(["slug_inconnu"])
        assert isinstance(block, str)

    def test_multiple_skills_in_block(self, sm, skills_dir):
        _write(skills_dir, "a", "---\nname: Alpha\ndescription: d.\n---\nContenu A.")
        _write(skills_dir, "b", "---\nname: Beta\ndescription: d.\n---\nContenu B.")
        sm.refresh()
        block = sm.build_pinned_block(["a", "b"])
        assert "Alpha" in block and "Beta" in block

    def test_header_footer_present(self, sm, skills_dir):
        _write(skills_dir, "ps", VALID)
        sm.refresh()
        block = sm.build_pinned_block(["ps"])
        assert "Skills actifs" in block or "Fin des skills" in block
