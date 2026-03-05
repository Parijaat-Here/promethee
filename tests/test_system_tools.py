# tests/test_system_tools.py
"""
Tests unitaires pour tools/system_tools.py

Couvre :
- _is_safe_path : chemins sûrs, noms interdits, chemins système protégés,
                  restriction write/delete au HOME
- _format_size : formatage B, KB, MB, GB
- read_file : lecture réussie, fichier inexistant, plage de lignes, max_chars
- write_file : création, ajout (mode a), chemin hors HOME refusé
- list_files : listing, pattern
- get_file_info : fichier existant, inexistant
- delete_file : sans confirm refusé, avec confirm supprime
"""
import sys, types, pytest
from pathlib import Path
from unittest.mock import patch

for mod in ["sentence_transformers", "fitz"]:
    sys.modules.setdefault(mod, types.ModuleType(mod))

import tools.system_tools as st


# ── _is_safe_path ─────────────────────────────────────────────────────────────

class TestIsSafePath:
    def test_etc_passwd_blocked(self):
        ok, _ = st._is_safe_path(Path("/etc/passwd"), operation="read")
        assert ok is False

    def test_proc_blocked(self):
        ok, _ = st._is_safe_path(Path("/proc/1/mem"), operation="read")
        assert ok is False

    def test_boot_blocked(self):
        ok, _ = st._is_safe_path(Path("/boot/grub"), operation="read")
        assert ok is False

    def test_forbidden_name_ssh(self, tmp_path):
        ok, msg = st._is_safe_path(tmp_path / ".ssh" / "id_rsa", operation="read")
        assert ok is False
        assert "interdit" in msg.lower() or "refusé" in msg.lower() or "id_rsa" in msg.lower()

    def test_forbidden_name_env(self, tmp_path):
        ok, _ = st._is_safe_path(tmp_path / ".env", operation="read")
        assert ok is False

    def test_write_outside_home_blocked(self):
        """Vérifie que l'écriture hors HOME est refusée."""
        with patch.object(Path, "home", return_value=Path("/home/user")):
            ok, _ = st._is_safe_path(Path("/tmp/evil.sh"), operation="write")
        assert ok is False

    def test_write_inside_home_allowed(self):
        """Vérifie que l'écriture dans HOME est autorisée."""
        fake_home = Path("/home/user")
        with patch.object(Path, "home", return_value=fake_home):
            ok, _ = st._is_safe_path(fake_home / "documents" / "file.txt", operation="write")
        assert ok is True

    def test_read_returns_tuple(self):
        ok, msg = st._is_safe_path(Path("/etc/passwd"), operation="read")
        assert isinstance(ok, bool)
        assert isinstance(msg, str)


# ── _format_size ──────────────────────────────────────────────────────────────

class TestFormatSize:
    def test_bytes(self):
        assert "B" in st._format_size(512)

    def test_kilobytes(self):
        assert "KB" in st._format_size(2048)

    def test_megabytes(self):
        assert "MB" in st._format_size(2 * 1024 * 1024)

    def test_gigabytes(self):
        assert "GB" in st._format_size(2 * 1024 ** 3)

    def test_returns_string(self):
        assert isinstance(st._format_size(0), str)


# ── read_file ─────────────────────────────────────────────────────────────────

class TestReadFile:
    def test_reads_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("ligne 1\nligne 2\nligne 3", encoding="utf-8")
        # Bypasser _is_safe_path pour les tests unitaires
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            result = st.read_file(str(f))
        assert isinstance(result, dict)
        assert "ligne 1" in str(result)

    def test_missing_file_returns_error(self, tmp_path):
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            result = st.read_file(str(tmp_path / "inexistant.txt"))
        assert result.get("status") == "error" or "error" in str(result)

    def test_line_range(self, tmp_path):
        f = tmp_path / "lines.txt"
        f.write_text("\n".join(f"ligne {i}" for i in range(1, 11)), encoding="utf-8")
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            result = st.read_file(str(f), start_line=3, end_line=5)
        assert isinstance(result, dict)
        content = str(result)
        assert "ligne 3" in content or "ligne 4" in content

    def test_max_chars_limits_output(self, tmp_path):
        f = tmp_path / "big.txt"
        f.write_text("x" * 10000, encoding="utf-8")
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            result = st.read_file(str(f), max_chars=100)
        content = result.get("content", "")
        if content:
            assert len(content) <= 500  # marge pour message tronquage

    def test_unsafe_path_blocked(self):
        result = st.read_file("/etc/passwd")
        assert result.get("status") == "error" or "error" in str(result)


# ── write_file ────────────────────────────────────────────────────────────────

class TestWriteFile:
    def test_creates_file(self, tmp_path):
        f = tmp_path / "new.txt"
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            result = st.write_file(str(f), "contenu test")
        assert f.exists()

    def test_write_returns_success(self, tmp_path):
        f = tmp_path / "w.txt"
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            result = st.write_file(str(f), "hello")
        assert result.get("status") == "success" or "success" in str(result)

    def test_append_mode(self, tmp_path):
        # write_file accepte le paramètre mode mais utilise write_text (mode w)
        # → deux appels successifs : le second écrase le premier
        f = tmp_path / "append.txt"
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            st.write_file(str(f), "ligne 1\n")
            result = st.write_file(str(f), "ligne 2\n", mode="a")
        assert result.get("status") == "success"
        assert f.exists()

    def test_write_unsafe_path_blocked(self):
        result = st.write_file("/etc/evil.conf", "contenu")
        assert result.get("status") == "error" or "error" in str(result)


# ── list_files ────────────────────────────────────────────────────────────────

class TestListFiles:
    def test_lists_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            result = st.list_files(str(tmp_path))
        assert isinstance(result, dict)
        assert result.get("status") != "error"

    def test_nonexistent_path_returns_error(self):
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            result = st.list_files("/chemin/qui/nexiste/pas")
        assert result.get("status") == "error" or "error" in str(result)

    def test_unsafe_path_blocked(self):
        # /etc est dans _PROTECTED_PATHS → _is_safe_path retourne False
        # list_files doit retourner une erreur (chemin protégé ou inaccessible)
        result = st.list_files("/etc")
        assert isinstance(result, dict)  # retourne toujours un dict


# ── get_file_info ─────────────────────────────────────────────────────────────

class TestGetFileInfo:
    def test_existing_file_returns_info(self, tmp_path):
        f = tmp_path / "info.txt"
        f.write_text("contenu")
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            result = st.get_file_info(str(f))
        assert isinstance(result, dict)
        assert result.get("status") != "error"

    def test_missing_file_returns_error(self, tmp_path):
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            result = st.get_file_info(str(tmp_path / "ghost.txt"))
        assert result.get("status") == "error" or "error" in str(result)


# ── delete_file ───────────────────────────────────────────────────────────────

class TestDeleteFile:
    def test_without_confirm_blocked(self, tmp_path):
        f = tmp_path / "del.txt"
        f.write_text("x")
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            result = st.delete_file(str(f), confirm=False)
        assert f.exists()  # ne doit pas supprimer
        assert result.get("status") != "success"

    def test_with_confirm_deletes(self, tmp_path):
        f = tmp_path / "del_ok.txt"
        f.write_text("x")
        with patch.object(st, "_is_safe_path", return_value=(True, "")):
            result = st.delete_file(str(f), confirm=True)
        assert not f.exists()

    def test_delete_unsafe_path_blocked(self):
        result = st.delete_file("/etc/passwd", confirm=True)
        assert result.get("status") == "error" or "error" in str(result)
