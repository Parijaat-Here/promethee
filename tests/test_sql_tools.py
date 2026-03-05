# tests/test_sql_tools.py
"""
Tests unitaires pour tools/sql_tools.py

Couvre les helpers purs (sans connexion réseau) :
- _detect_driver : sqlite, postgresql, mysql, URL invalide
- _safe_url : masquage du mot de passe
- _is_destructive : SELECT (non), DROP/DELETE/UPDATE (oui)
- sql_connect / sql_disconnect / sql_list_connections : avec SQLite in-memory
- sql_list_tables : après connexion SQLite
- sql_query : SELECT sur SQLite
- sql_execute : CREATE/INSERT sur SQLite (mode non read-only)
"""
import sys, types, pytest

for mod in ["sentence_transformers", "fitz"]:
    sys.modules.setdefault(mod, types.ModuleType(mod))

import tools.sql_tools as sq


# ── _detect_driver ────────────────────────────────────────────────────────────

class TestDetectDriver:
    def test_sqlite(self):
        assert sq._detect_driver("sqlite:///test.db") == "sqlite"

    def test_sqlite_memory(self):
        assert sq._detect_driver("sqlite:///:memory:") == "sqlite"

    def test_postgresql(self):
        assert sq._detect_driver("postgresql://user:pass@host/db") == "postgresql"

    def test_postgres_alias(self):
        assert sq._detect_driver("postgres://host/db") == "postgresql"

    def test_mysql(self):
        assert sq._detect_driver("mysql://user:pass@host/db") == "mysql"

    def test_mariadb(self):
        assert sq._detect_driver("mariadb://host/db") == "mysql"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            sq._detect_driver("http://not-a-db")

    def test_empty_raises(self):
        with pytest.raises((ValueError, Exception)):
            sq._detect_driver("")


# ── _safe_url ─────────────────────────────────────────────────────────────────

class TestSafeUrl:
    def test_masks_password(self):
        result = sq._safe_url("postgresql://user:secret123@host/db")
        assert "secret123" not in result
        assert "****" in result

    def test_no_password_unchanged(self):
        url = "sqlite:///mydb.db"
        assert sq._safe_url(url) == url

    def test_user_preserved(self):
        result = sq._safe_url("postgresql://user:pass@host/db")
        assert "user" in result


# ── _is_destructive ───────────────────────────────────────────────────────────

class TestIsDestructive:
    def test_select_not_destructive(self):
        assert sq._is_destructive("SELECT * FROM t") is False

    def test_select_uppercase(self):
        assert sq._is_destructive("SELECT id FROM users") is False

    def test_drop_destructive(self):
        assert sq._is_destructive("DROP TABLE users") is True

    def test_delete_destructive(self):
        assert sq._is_destructive("DELETE FROM t WHERE id=1") is True

    def test_update_destructive(self):
        assert sq._is_destructive("UPDATE t SET x=1") is True

    def test_insert_destructive(self):
        assert sq._is_destructive("INSERT INTO t VALUES (1)") is True

    def test_create_destructive(self):
        assert sq._is_destructive("CREATE TABLE t (id INT)") is True

    def test_truncate_destructive(self):
        assert sq._is_destructive("TRUNCATE TABLE t") is True

    def test_empty_not_destructive(self):
        assert sq._is_destructive("") is False

    def test_lowercase_select(self):
        assert sq._is_destructive("select * from t") is False

    def test_lowercase_delete(self):
        assert sq._is_destructive("delete from t") is True


# ── sql_connect / disconnect / list ──────────────────────────────────────────

class TestSqlConnectDisconnect:
    @pytest.fixture(autouse=True)
    def cleanup(self):
        yield
        # Fermer toutes les connexions de test
        for nom in list(sq._CONNECTIONS.keys()):
            try:
                sq._CONNECTIONS[nom]["conn"].close()
            except Exception:
                pass
            sq._CONNECTIONS.pop(nom, None)

    def test_connect_sqlite_memory(self):
        result = sq.sql_connect("sqlite:///:memory:", nom="test_conn")
        assert isinstance(result, dict)
        assert result.get("status") == "success" or "success" in str(result)

    def test_connect_registers_connection(self):
        sq.sql_connect("sqlite:///:memory:", nom="test_reg")
        assert "test_reg" in sq._CONNECTIONS

    def test_disconnect_removes_connection(self):
        sq.sql_connect("sqlite:///:memory:", nom="test_disc")
        sq.sql_disconnect("test_disc")
        assert "test_disc" not in sq._CONNECTIONS

    def test_disconnect_unknown_returns_error(self):
        result = sq.sql_disconnect("connexion_inexistante")
        assert result.get("status") == "error" or "error" in str(result)

    def test_list_connections_empty(self):
        result = sq.sql_list_connections()
        assert isinstance(result, dict)

    def test_list_connections_shows_active(self):
        sq.sql_connect("sqlite:///:memory:", nom="test_list")
        result = sq.sql_list_connections()
        connections = result.get("connections", {})
        assert "test_list" in connections or "test_list" in str(result)


# ── sql_query ─────────────────────────────────────────────────────────────────

class TestSqlQuery:
    @pytest.fixture(autouse=True)
    def setup_db(self):
        sq.sql_connect("sqlite:///:memory:", nom="qtest")
        # Créer une table de test
        conn = sq._CONNECTIONS["qtest"]["conn"]
        conn.execute("CREATE TABLE items (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO items VALUES (1, 'alpha')")
        conn.execute("INSERT INTO items VALUES (2, 'beta')")
        conn.commit()
        yield
        try:
            sq._CONNECTIONS["qtest"]["conn"].close()
        except Exception:
            pass
        sq._CONNECTIONS.pop("qtest", None)

    def test_select_returns_dict(self):
        result = sq.sql_query("SELECT * FROM items", connexion="qtest")
        assert isinstance(result, dict)

    def test_select_returns_rows(self):
        result = sq.sql_query("SELECT * FROM items", connexion="qtest")
        rows = result.get("lignes") or result.get("rows") or result.get("results") or []
        assert len(rows) == 2

    def test_select_column_names(self):
        result = sq.sql_query("SELECT id, name FROM items", connexion="qtest")
        assert isinstance(result, dict)

    def test_unknown_connection_returns_error(self):
        result = sq.sql_query("SELECT 1", connexion="conn_inexistante")
        assert result.get("status") == "error" or "error" in str(result)

    def test_invalid_sql_returns_error(self):
        result = sq.sql_query("SELECT FROM WHERE", connexion="qtest")
        assert result.get("status") == "error" or "error" in str(result)


# ── sql_execute ───────────────────────────────────────────────────────────────

class TestSqlExecute:
    @pytest.fixture(autouse=True)
    def setup_db(self):
        sq.sql_connect("sqlite:///:memory:", nom="extest")
        yield
        try:
            sq._CONNECTIONS["extest"]["conn"].close()
        except Exception:
            pass
        sq._CONNECTIONS.pop("extest", None)

    def test_create_table(self):
        result = sq.sql_execute("CREATE TABLE t (id INT)", connexion="extest")
        assert isinstance(result, dict)
        assert result.get("status") == "success" or "error" not in str(result).lower()

    def test_insert_row(self):
        sq.sql_execute("CREATE TABLE t2 (val TEXT)", connexion="extest")
        result = sq.sql_execute("INSERT INTO t2 VALUES ('hello')", connexion="extest")
        assert isinstance(result, dict)

    def test_read_only_blocks_write(self):
        sq.sql_connect("sqlite:///:memory:", nom="rotest", read_only=True)
        result = sq.sql_execute("CREATE TABLE ro (x INT)", connexion="rotest")
        assert result.get("status") == "error" or "error" in str(result)
        sq._CONNECTIONS.pop("rotest", None)
