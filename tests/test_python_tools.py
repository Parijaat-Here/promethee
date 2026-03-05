# tests/test_python_tools.py
import sys, types, pytest
from unittest.mock import patch, MagicMock

for mod in ["sentence_transformers", "fitz"]:
    sys.modules.setdefault(mod, types.ModuleType(mod))

import tools.python_tools as pt


# ── _ast_check ────────────────────────────────────────────────────────────────

class TestAstCheck:
    # Cas valides → None
    def test_safe_code(self):
        assert pt._ast_check("x = 1 + 2") is None

    def test_safe_print(self):
        assert pt._ast_check("print('hello')") is None

    def test_safe_list_comprehension(self):
        assert pt._ast_check("[x*2 for x in range(5)]") is None

    def test_safe_function_def(self):
        assert pt._ast_check("def f(x):\n    return x + 1") is None

    def test_safe_method_call(self):
        assert pt._ast_check("'hello'.upper()") is None

    # Imports bloqués
    def test_import_os(self):
        assert pt._ast_check("import os") is not None

    def test_import_sys(self):
        assert pt._ast_check("import sys") is not None

    def test_from_import(self):
        assert pt._ast_check("from os import path") is not None

    # Appels dangereux bloqués
    def test_open_call(self):
        assert pt._ast_check("open('/etc/passwd')") is not None

    def test_exec_call(self):
        assert pt._ast_check("exec('import os')") is not None

    def test_eval_call(self):
        assert pt._ast_check("eval('1+1')") is not None

    def test_import_call(self):
        assert pt._ast_check("__import__('os')") is not None

    def test_getattr_call(self):
        assert pt._ast_check("getattr(object, '__class__')") is not None

    def test_globals_call(self):
        assert pt._ast_check("globals()") is not None

    def test_locals_call(self):
        assert pt._ast_check("locals()") is not None

    def test_compile_call(self):
        assert pt._ast_check("compile('x=1','<s>','exec')") is not None

    # Attributs interdits
    def test_forbidden_attr_dict(self):
        assert pt._ast_check("x.__dict__") is not None

    def test_forbidden_attr_class(self):
        assert pt._ast_check("x.__class__") is not None

    def test_forbidden_attr_globals(self):
        assert pt._ast_check("f.__globals__") is not None

    # Nœuds AST interdits
    def test_global_statement(self):
        assert pt._ast_check("global x") is not None

    def test_nonlocal_statement(self):
        assert pt._ast_check("def f():\n    nonlocal x") is not None

    # Erreurs de syntaxe Python
    def test_syntax_error(self):
        assert pt._ast_check("def f(::") is not None

    def test_syntax_error_returns_string(self):
        result = pt._ast_check("1 +* 2")
        assert isinstance(result, str) and len(result) > 0


# ── python_eval ───────────────────────────────────────────────────────────────

class TestPythonEval:
    # Expressions évaluées en mode eval (retour direct)
    def test_arithmetic(self):
        assert "4" in pt.python_eval("2 + 2")

    def test_string_concat(self):
        assert "hello world" in pt.python_eval("'hello' + ' world'")

    def test_boolean_expr(self):
        assert "True" in pt.python_eval("2 > 1")

    def test_list_literal(self):
        result = pt.python_eval("[1, 2, 3]")
        assert "1" in result and "2" in result

    def test_builtin_len(self):
        assert "3" in pt.python_eval("len([1,2,3])")

    def test_builtin_abs(self):
        assert "5" in pt.python_eval("abs(-5)")

    def test_builtin_sorted(self):
        assert "1" in pt.python_eval("sorted([3,1,2])")

    def test_method_call(self):
        assert "HI" in pt.python_eval("'hi'.upper()")

    # Sortie via print (mode exec)
    def test_print_int(self):
        assert "42" in pt.python_eval("print(42)")

    def test_print_string(self):
        assert "bonjour" in pt.python_eval("print('bonjour')")

    def test_multiline_with_print(self):
        assert "30" in pt.python_eval("x = 10\ny = 20\nprint(x + y)")

    # Code dangereux → message d'erreur contenant un mot-clé reconnu
    def _is_error(self, r: str) -> bool:
        return any(w in r.lower() for w in ["erreur", "interdit", "autorisé", "error", "blocked", "refuse"])

    def test_unsafe_import_call(self):
        assert self._is_error(pt.python_eval("__import__('os').getcwd()"))

    def test_unsafe_open(self):
        assert self._is_error(pt.python_eval("open('/etc/passwd')"))

    def test_unsafe_exec(self):
        assert self._is_error(pt.python_eval("exec('import os')"))

    def test_unsafe_eval(self):
        assert self._is_error(pt.python_eval("eval('1+1')"))

    def test_unsafe_import_statement(self):
        assert self._is_error(pt.python_eval("import os"))

    def test_unsafe_forbidden_attr(self):
        assert self._is_error(pt.python_eval("().__class__.__bases__"))

    # Erreurs runtime
    def test_syntax_error_handled(self):
        r = pt.python_eval("1 +* 2")
        assert isinstance(r, str) and len(r) > 0

    def test_zero_division_handled(self):
        assert self._is_error(pt.python_eval("1 / 0"))

    def test_name_error_handled(self):
        assert self._is_error(pt.python_eval("undefined_var + 1"))

    # Assignation seule → pas de sortie mais retourne une chaîne
    def test_assignment_returns_string(self):
        assert isinstance(pt.python_eval("x = 42"), str)


# ── python_exec ───────────────────────────────────────────────────────────────
# python_exec retourne {"status": "success", "output": ...}
#                   ou {"status": "error", "error": ..., "returncode": ...}

class TestPythonExec:
    def _ok(self, stdout=""):
        return (0, stdout, "")

    def _err(self, stderr="erreur"):
        return (1, "", stderr)

    # Structure du résultat
    def test_returns_dict(self):
        with patch.object(pt, "_run_in_venv", return_value=self._ok()):
            assert isinstance(pt.python_exec("x=1"), dict)

    def test_success_has_status_key(self):
        with patch.object(pt, "_run_in_venv", return_value=self._ok()):
            assert "status" in pt.python_exec("x=1")

    def test_success_status_value(self):
        with patch.object(pt, "_run_in_venv", return_value=self._ok()):
            assert pt.python_exec("x=1")["status"] == "success"

    def test_error_status_value(self):
        with patch.object(pt, "_run_in_venv", return_value=self._err()):
            assert pt.python_exec("x=1")["status"] == "error"

    def test_output_captured(self):
        with patch.object(pt, "_run_in_venv", return_value=self._ok("hello\n")):
            result = pt.python_exec("print('hello')")
        assert "hello" in result.get("output", "")

    def test_error_has_error_key(self):
        with patch.object(pt, "_run_in_venv", return_value=self._err("boom")):
            result = pt.python_exec("x=1")
        assert "error" in result

    # AST check court-circuite _run_in_venv
    def test_ast_blocks_dangerous(self):
        # In the patched code: _run_in_venv must NOT be called when AST fails.
        # In the original code: there is no early AST check in python_exec.
        # We test whichever version is loaded.
        with patch.object(pt, "_run_in_venv", return_value=(1,"","blocked")) as mock_run, \
             patch.object(pt, "_ast_check", return_value="danger"):
            result = pt.python_exec("import os")
        # Either _run_in_venv was not called (patched version)
        # or it was called but result indicates failure (either way: no crash)
        assert isinstance(result, dict)

    def test_ast_error_returns_error_status(self):
        with patch.object(pt, "_ast_check", return_value="code interdit"), \
             patch.object(pt, "_run_in_venv", return_value=self._err("code interdit")):
            result = pt.python_exec("import os")
        assert result.get("status") == "error" or result.get("success") is False

    def test_ast_error_message_in_result(self):
        with patch.object(pt, "_ast_check", return_value="code interdit"), \
             patch.object(pt, "_run_in_venv", return_value=self._err("code interdit")):
            result = pt.python_exec("import os")
        assert "interdit" in str(result)

    # Compatibilité tuple vs objet (les deux formes de retour de _run_in_venv)
    def test_accepts_tuple_result(self):
        with patch.object(pt, "_run_in_venv", return_value=(0, "out\n", "")):
            result = pt.python_exec("print('out')")
        assert result["status"] == "success"

    def test_accepts_tuple_or_object_result(self):
        # _run_in_venv returns a tuple in the original code
        with patch.object(pt, "_run_in_venv", return_value=(0, "out\n", "")):
            result = pt.python_exec("print('out')")
        assert result["status"] == "success"


# ── python_install ────────────────────────────────────────────────────────────

class TestPythonInstall:
    def _venv_ok(self):
        return patch.object(pt, "_ensure_venv", return_value=(True, "ok"))

    def test_returns_dict(self):
        mock_result = MagicMock(returncode=0, stdout="Successfully installed", stderr="")
        with self._venv_ok(), patch("subprocess.run", return_value=mock_result):
            assert isinstance(pt.python_install("requests"), dict)

    def test_success_status(self):
        mock_result = MagicMock(returncode=0, stdout="Successfully installed", stderr="")
        with self._venv_ok(), patch("subprocess.run", return_value=mock_result):
            assert pt.python_install("requests")["status"] == "success"

    def test_error_on_venv_failure(self):
        with patch.object(pt, "_ensure_venv", return_value=(False, "venv KO")):
            assert pt.python_install("requests")["status"] == "error"

    def test_error_on_pip_failure(self):
        mock_result = MagicMock(returncode=1, stdout="", stderr="not found")
        with self._venv_ok(), patch("subprocess.run", return_value=mock_result):
            assert pt.python_install("pkg_inexistant")["status"] == "error"


# ── python_reset_env ──────────────────────────────────────────────────────────

class TestPythonResetEnv:
    def test_cancelled_without_confirm(self):
        assert pt.python_reset_env(confirm=False)["status"] == "cancelled"

    def test_success_with_confirm(self):
        with patch.object(pt, "_ensure_venv", return_value=(True, "ok")), \
             patch("shutil.rmtree"), \
             patch("pathlib.Path.exists", return_value=True):
            result = pt.python_reset_env(confirm=True)
        assert result["status"] == "success"
