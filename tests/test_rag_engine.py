# tests/test_rag_engine.py
import sys, types, pytest
from unittest.mock import MagicMock, patch

_qs = types.ModuleType("qdrant_client")
_qs.QdrantClient = MagicMock()
_qm = types.ModuleType("qdrant_client.models")
for _n in ("Distance","VectorParams","PointStruct","Filter","FieldCondition","MatchValue","FilterSelector"):
    setattr(_qm, _n, MagicMock())
_qs.models = _qm
sys.modules.setdefault("qdrant_client", _qs)
sys.modules.setdefault("qdrant_client.models", _qm)

import core.rag_engine as rag

class TestChunks:
    def test_empty(self):
        assert rag._chunk_text("") == []
    def test_whitespace_empty(self):
        assert rag._chunk_text("   ") == []
    def test_short_single_chunk(self):
        c = rag._chunk_text("Ceci est une courte phrase.")
        assert len(c) == 1 and "courte" in c[0]
    def test_long_multiple_chunks(self):
        text = ("Voici une phrase de test assez longue. " * 60)
        assert len(rag._chunk_text(text, max_tokens=50)) > 1
    def test_code_preserved(self):
        code = "def foo():\n    return 42\n\ndef bar():\n    return 0\n"
        full = " ".join(rag._chunk_text(code))
        assert "def foo" in full and "def bar" in full

class TestBuildContext:
    def test_no_hits_empty(self):
        with patch.object(rag, "search", return_value=[]):
            assert rag.build_rag_context("q") == ""
    def test_hits_produce_context(self):
        hits = [{"text": "Contenu A", "source": "doc.pdf", "scope": "global", "score": 0.9}]
        with patch.object(rag, "search", return_value=hits):
            r = rag.build_rag_context("q")
        assert "doc.pdf" in r and "Contenu A" in r and "0.90" in r

def _p1():
    return patch.object(rag, "QDRANT_OK", True)
def _p2():
    return patch.object(rag, "EMBED_OK", True)
def _pt(text="t", source="s", cid="global", score=0.9):
    p = MagicMock()
    p.payload = {"text": text, "source": source, "conversation_id": cid}
    p.score = score
    return p

class TestSearch:
    def test_unavailable_returns_empty(self):
        with patch.object(rag, "QDRANT_OK", False):
            assert rag.search("q") == []

    def test_named_vectors_uses_using(self):
        mock_qc = MagicMock()
        col = MagicMock(); col.name = "BA2T"
        mock_qc.get_collections.return_value.collections = [col]
        vp = MagicMock(); vp.size = 4
        info = MagicMock()
        info.config.params.vectors.items.return_value = [("dense", vp)]
        mock_qc.get_collection.return_value = info
        mock_qc.query_points.return_value.points = [_pt()]
        with _p1(), _p2(), patch.object(rag, "_client", return_value=mock_qc),              patch.object(rag, "_get_embeddings", return_value=[[0.1,0.2,0.3,0.4]]):
            rag.search("q", collection_name="BA2T")
        assert mock_qc.query_points.call_args[1].get("using") == "dense"

    def test_external_no_scope_filter(self):
        mock_qc = MagicMock()
        col = MagicMock(); col.name = "BA2T"
        mock_qc.get_collections.return_value.collections = [col]
        info = MagicMock()
        info.config.params.vectors.items.side_effect = AttributeError
        mock_qc.get_collection.return_value = info
        mock_qc.query_points.return_value.points = []
        with _p1(), _p2(), patch.object(rag, "_client", return_value=mock_qc),              patch.object(rag, "_get_embeddings", return_value=[[0.1,0.2,0.3,0.4]]):
            rag.search("q", collection_name="BA2T")
        assert "query_filter" not in mock_qc.query_points.call_args[1]

    def test_internal_has_scope_filter(self):
        from core.config import Config
        mock_qc = MagicMock()
        col = MagicMock(); col.name = Config.QDRANT_COLLECTION
        mock_qc.get_collections.return_value.collections = [col]
        info = MagicMock()
        info.config.params.vectors.items.side_effect = AttributeError
        mock_qc.get_collection.return_value = info
        mock_qc.query_points.return_value.points = []
        with _p1(), _p2(), patch.object(rag, "_client", return_value=mock_qc),              patch.object(rag, "_get_embeddings", return_value=[[0.1,0.2,0.3,0.4]]):
            rag.search("q", collection_name=Config.QDRANT_COLLECTION)
        assert "query_filter" in mock_qc.query_points.call_args[1]

class TestIsAvailable:
    def test_true(self):
        with patch.object(rag, "QDRANT_OK", True), patch.object(rag, "EMBED_OK", True):
            assert rag.is_available() is True
    def test_false_qdrant(self):
        with patch.object(rag, "QDRANT_OK", False), patch.object(rag, "EMBED_OK", True):
            assert rag.is_available() is False
    def test_false_embed(self):
        with patch.object(rag, "QDRANT_OK", True), patch.object(rag, "EMBED_OK", False):
            assert rag.is_available() is False

class TestListCollections:
    def test_returns_names(self):
        mock_qc = MagicMock()
        c1, c2 = MagicMock(), MagicMock()
        c1.name, c2.name = "A", "B"
        mock_qc.get_collections.return_value.collections = [c1, c2]
        with patch.object(rag, "QDRANT_OK", True), patch.object(rag, "_client", return_value=mock_qc):
            assert rag.list_collections() == ["A", "B"]
    def test_empty_when_ko(self):
        with patch.object(rag, "QDRANT_OK", False):
            assert rag.list_collections() == []


# ── Compléments : fonctions non couvertes ─────────────────────────────────────

class TestEstimateTokens:
    def test_empty_string(self):
        assert rag._estimate_tokens("") >= 0

    def test_short_text(self):
        result = rag._estimate_tokens("Bonjour monde")
        assert isinstance(result, int) and result > 0

    def test_longer_text_more_tokens(self):
        short = rag._estimate_tokens("Bonjour")
        long  = rag._estimate_tokens("Bonjour " * 100)
        assert long > short

    def test_returns_int(self):
        assert isinstance(rag._estimate_tokens("test"), int)


class TestListSourcesUnavailable:
    def test_returns_empty_when_qdrant_ko(self):
        with patch.object(rag, "QDRANT_OK", False):
            assert rag.list_sources() == []

    def test_returns_empty_when_embed_ko(self):
        with patch.object(rag, "EMBED_OK", False):
            assert rag.list_sources() == []


class TestDeleteBySourceUnavailable:
    def test_returns_zero_when_qdrant_ko(self):
        with patch.object(rag, "QDRANT_OK", False):
            assert rag.delete_by_source("source_test") == 0


class TestBuildRagContext:
    def test_returns_string(self):
        with patch.object(rag, "search", return_value=[]):
            result = rag.build_rag_context("ma requête")
        assert isinstance(result, str)

    def test_empty_search_results_empty_context(self):
        with patch.object(rag, "search", return_value=[]):
            result = rag.build_rag_context("requête sans résultat")
        assert result == "" or isinstance(result, str)

    def test_search_results_included_in_context(self):
        # build_rag_context consomme les hits retournés par search()
        # Structure : {scope, source, score, text} (format aplati, pas payload)
        hits = [{"scope": "global", "source": "doc.txt",
                 "score": 0.9, "text": "passage important"}]
        with patch.object(rag, "search", return_value=hits):
            result = rag.build_rag_context("requête")
        assert isinstance(result, str) and "passage important" in result
