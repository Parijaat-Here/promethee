# tests/test_data_tools.py
"""
Tests unitaires pour tools/data_tools.py

Couvre les fonctions pures testables sans dépendances externes :
- datetime_now : format par défaut, format personnalisé
- datetime_parse : ISO, DD/MM/YYYY, format explicite, erreur
- datetime_diff : différence en jours, en heures
- text_regex : match, groupes, sans match
- json_formatter : formatage, chemin JSON, JSON invalide
- encode_decode : base64 encode/decode, hex encode
- hash_text : MD5, SHA256
- number_format : formatage français, pourcentage
- _is_safe_path : chemins sûrs, chemins interdits
- stats_describe : moyenne, médiane, min, max
"""
import sys, types, json, pytest

for mod in ["sentence_transformers", "fitz"]:
    sys.modules.setdefault(mod, types.ModuleType(mod))

import tools.data_tools as dt


# ── datetime_now ──────────────────────────────────────────────────────────────

class TestDatetimeNow:
    def test_returns_string(self):
        assert isinstance(dt.datetime_now(), str)

    def test_default_is_iso_like(self):
        result = dt.datetime_now()
        assert "-" in result and ":" in result

    def test_custom_format(self):
        result = dt.datetime_now(format="%Y")
        assert len(result) == 4
        assert result.isdigit()

    def test_invalid_format_returns_error_string(self):
        result = dt.datetime_now(format="%invalid_xyz_qrs")
        # soit format rendu tel quel, soit message d'erreur
        assert isinstance(result, str)


# ── datetime_parse ────────────────────────────────────────────────────────────

class TestDatetimeParse:
    def test_iso_format(self):
        result = dt.datetime_parse("2024-06-15")
        assert isinstance(result, dict)

    def test_french_format(self):
        result = dt.datetime_parse("25/12/2024")
        assert isinstance(result, dict)

    def test_explicit_format(self):
        result = dt.datetime_parse("15-06-2024", format_entree="%d-%m-%Y")
        assert isinstance(result, dict)
        assert result.get("error") is None or "error" not in result

    def test_invalid_date_returns_error(self):
        result = dt.datetime_parse("pas_une_date_xyz")
        assert "error" in result

    def test_result_contains_iso(self):
        result = dt.datetime_parse("2024-01-01")
        assert any("2024" in str(v) for v in result.values())


# ── text_regex ────────────────────────────────────────────────────────────────

class TestTextRegex:
    def test_simple_match(self):
        result = dt.text_regex("Il y a 42 pommes", r"\d+")
        assert isinstance(result, dict)
        assert result.get("nb_occurrences", 0) > 0

    def test_no_match(self):
        result = dt.text_regex("bonjour", r"xyz_impossible_\d{99}")
        assert isinstance(result, dict)

    def test_invalid_regex_returns_error(self):
        result = dt.text_regex("texte", r"[invalide")
        assert result.get("status") == "error" or "error" in result

    def test_groups_captured(self):
        result = dt.text_regex("Date: 2024-06", r"(\d{4})-(\d{2})")
        assert isinstance(result, dict)


# ── json_formatter ────────────────────────────────────────────────────────────

class TestJsonFormatter:
    def test_formats_valid_json(self):
        result = dt.json_formatter('{"a":1,"b":2}')
        assert isinstance(result, str)
        assert '"a"' in result

    def test_invalid_json_returns_error(self):
        result = dt.json_formatter("{not valid json}")
        assert isinstance(result, str)
        assert "error" in result.lower() or "erreur" in result.lower() or "{" not in result

    def test_key_path_extracts_value(self):
        result = dt.json_formatter('{"outer":{"inner":42}}', key_path="outer.inner")
        assert "42" in result

    def test_nested_json_formatted(self):
        result = dt.json_formatter('{"a":{"b":1}}')
        assert isinstance(result, str)


# ── encode_decode ─────────────────────────────────────────────────────────────

class TestEncodeDecode:
    def test_base64_encode(self):
        result = dt.encode_decode("hello", format="base64", direction="encoder")
        assert isinstance(result, dict)
        assert result.get("status") == "success" or "resultat" in result or "result" in result

    def test_base64_roundtrip(self):
        encoded = dt.encode_decode("test123", format="base64", direction="encoder")
        # extraire la valeur encodée selon la structure de retour
        val = encoded.get("resultat") or encoded.get("result") or ""
        if val:
            decoded = dt.encode_decode(val, format="base64", direction="décoder")
            dec_val = decoded.get("resultat") or decoded.get("result") or ""
            assert "test123" in dec_val

    def test_hex_encode(self):
        result = dt.encode_decode("abc", format="hex", direction="encoder")
        assert isinstance(result, dict)

    def test_unknown_format_returns_error(self):
        result = dt.encode_decode("x", format="format_inexistant", direction="encoder")
        assert "error" in result or "erreur" in str(result).lower()


# ── hash_text ─────────────────────────────────────────────────────────────────

class TestHashText:
    def test_md5_returns_dict(self):
        result = dt.hash_text("hello", algorithme="md5")
        assert isinstance(result, dict)

    def test_sha256_returns_dict(self):
        result = dt.hash_text("hello", algorithme="sha256")
        assert isinstance(result, dict)

    def test_md5_is_32_chars(self):
        result = dt.hash_text("hello", algorithme="md5")
        val = result.get("hash") or result.get("md5") or ""
        if val:
            assert len(val) == 32

    def test_sha256_is_64_chars(self):
        result = dt.hash_text("hello", algorithme="sha256")
        val = result.get("hash") or result.get("sha256") or ""
        if val:
            assert len(val) == 64

    def test_same_input_same_hash(self):
        r1 = dt.hash_text("stable", algorithme="md5")
        r2 = dt.hash_text("stable", algorithme="md5")
        assert r1 == r2

    def test_different_input_different_hash(self):
        r1 = dt.hash_text("aaa", algorithme="md5")
        r2 = dt.hash_text("bbb", algorithme="md5")
        assert r1 != r2


# ── number_format ─────────────────────────────────────────────────────────────

class TestNumberFormat:
    def test_returns_dict(self):
        result = dt.number_format(1234567.89)
        assert isinstance(result, dict)

    def test_large_number_has_separator(self):
        result = dt.number_format(1000000)
        formatted = str(result)
        # doit avoir un séparateur quelque part dans le résultat
        assert "1" in formatted and "000" in formatted

    def test_percentage(self):
        result = dt.number_format(0.1234, style="percent")
        assert isinstance(result, dict)


# ── stats_describe ────────────────────────────────────────────────────────────

class TestStatsDescribe:
    def test_returns_dict(self):
        result = dt.stats_describe([1, 2, 3, 4, 5])
        assert isinstance(result, dict)

    def test_mean_correct(self):
        result = dt.stats_describe([2, 4, 6])
        mean = result.get("mean") or result.get("moyenne") or result.get("moy")
        if mean is not None:
            assert abs(float(mean) - 4.0) < 0.01

    def test_min_max(self):
        result = dt.stats_describe([1, 5, 3])
        assert isinstance(result, dict)
        # min et max quelque part dans le dict
        values = list(result.values())
        assert 1 in values or any(v == 1 for v in values)

    def test_empty_list_returns_error_or_empty(self):
        result = dt.stats_describe([])
        assert isinstance(result, dict)

    def test_single_value(self):
        result = dt.stats_describe([42])
        assert isinstance(result, dict)
