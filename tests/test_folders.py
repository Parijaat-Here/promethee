# tests/test_folders.py
"""
Tests unitaires pour la feature Dossiers (database.py).

Couvre :
- create_folder / get_folder / get_folders / get_all_folders
- rename_folder / delete_folder
- move_conversation_to_folder / get_conversations_in_folder
- Contrainte de profondeur max 2 niveaux
- Cascade : suppression dossier -> conversations detachees ("sans dossier")
"""
import pytest
from core.database import HistoryDB


@pytest.fixture()
def db(tmp_db):
    return HistoryDB(db_path=tmp_db)


# ─── create_folder ───────────────────────────────────────────────────────────

class TestCreateFolder:
    def test_create_root_folder_returns_id(self, db):
        fid = db.create_folder("Projet Alpha")
        assert isinstance(fid, str) and len(fid) > 0

    def test_root_folder_has_no_parent(self, db):
        fid = db.create_folder("Racine")
        assert db.get_folder(fid)["parent_id"] is None

    def test_create_subfolder(self, db):
        parent = db.create_folder("Parent")
        child  = db.create_folder("Enfant", parent_id=parent)
        assert db.get_folder(child)["parent_id"] == parent

    def test_max_depth_2_levels(self, db):
        lvl1 = db.create_folder("Niveau 1")
        lvl2 = db.create_folder("Niveau 2", parent_id=lvl1)
        with pytest.raises(ValueError):
            db.create_folder("Niveau 3", parent_id=lvl2)

    def test_multiple_root_folders(self, db):
        for name in ("A", "B", "C"):
            db.create_folder(name)
        assert len(db.get_folders(parent_id=None)) == 3

    def test_position_auto_increments(self, db):
        f1 = db.create_folder("Premier")
        f2 = db.create_folder("Deuxieme")
        folders = db.get_folders()
        positions = {f["id"]: f["position"] for f in folders}
        assert positions[f1] < positions[f2]


# ─── get_folder / get_folders / get_all_folders ──────────────────────────────

class TestGetFolders:
    def test_get_folder_unknown_returns_none(self, db):
        assert db.get_folder("inexistant") is None

    def test_get_folders_root_only(self, db):
        r = db.create_folder("Racine")
        db.create_folder("Sous", parent_id=r)
        root_ids = [f["id"] for f in db.get_folders(parent_id=None)]
        assert r in root_ids

    def test_subfolders_not_in_root(self, db):
        r   = db.create_folder("Root")
        sub = db.create_folder("Sub", parent_id=r)
        root_ids = [f["id"] for f in db.get_folders(parent_id=None)]
        assert sub not in root_ids

    def test_get_folders_children_of_parent(self, db):
        r  = db.create_folder("Parent")
        c1 = db.create_folder("Enfant 1", parent_id=r)
        c2 = db.create_folder("Enfant 2", parent_id=r)
        ids = [f["id"] for f in db.get_folders(parent_id=r)]
        assert c1 in ids and c2 in ids

    def test_get_all_folders_returns_all(self, db):
        r  = db.create_folder("Root")
        c1 = db.create_folder("Child 1", parent_id=r)
        c2 = db.create_folder("Child 2", parent_id=r)
        ids = [f["id"] for f in db.get_all_folders()]
        assert r in ids and c1 in ids and c2 in ids


# ─── rename_folder ───────────────────────────────────────────────────────────

class TestRenameFolder:
    def test_rename_changes_name(self, db):
        fid = db.create_folder("Ancien nom")
        db.rename_folder(fid, "Nouveau nom")
        assert db.get_folder(fid)["name"] == "Nouveau nom"

    def test_rename_strips_whitespace(self, db):
        fid = db.create_folder("Test")
        db.rename_folder(fid, "  Nom propre  ")
        assert db.get_folder(fid)["name"] == "Nom propre"


# ─── delete_folder ───────────────────────────────────────────────────────────

class TestDeleteFolder:
    def test_delete_removes_folder(self, db):
        fid = db.create_folder("A supprimer")
        db.delete_folder(fid)
        assert db.get_folder(fid) is None

    def test_delete_removes_subfolders(self, db):
        parent = db.create_folder("Parent")
        child  = db.create_folder("Enfant", parent_id=parent)
        db.delete_folder(parent)
        assert db.get_folder(child) is None

    def test_delete_detaches_conversations_in_folder(self, db):
        fid = db.create_folder("Projet")
        cid = db.create_conversation(title="Conv dans dossier")
        db.move_conversation_to_folder(cid, fid)
        db.delete_folder(fid)
        conv = db.get_conversation(cid)
        assert conv is not None
        assert conv["folder_id"] is None

    def test_delete_detaches_conversations_in_subfolder(self, db):
        parent = db.create_folder("Parent")
        child  = db.create_folder("Enfant", parent_id=parent)
        cid    = db.create_conversation(title="Conv dans sous-dossier")
        db.move_conversation_to_folder(cid, child)
        db.delete_folder(parent)
        assert db.get_conversation(cid)["folder_id"] is None


# ─── move_conversation_to_folder ─────────────────────────────────────────────

class TestMoveConversation:
    def test_move_to_folder(self, db):
        fid = db.create_folder("Dossier")
        cid = db.create_conversation(title="Ma conv")
        db.move_conversation_to_folder(cid, fid)
        assert db.get_conversation(cid)["folder_id"] == fid

    def test_move_to_none_removes_from_folder(self, db):
        fid = db.create_folder("Dossier")
        cid = db.create_conversation(title="Ma conv")
        db.move_conversation_to_folder(cid, fid)
        db.move_conversation_to_folder(cid, None)
        assert db.get_conversation(cid)["folder_id"] is None

    def test_move_to_another_folder(self, db):
        f1  = db.create_folder("D1")
        f2  = db.create_folder("D2")
        cid = db.create_conversation(title="Conv")
        db.move_conversation_to_folder(cid, f1)
        db.move_conversation_to_folder(cid, f2)
        assert db.get_conversation(cid)["folder_id"] == f2


# ─── get_conversations_in_folder ─────────────────────────────────────────────

class TestGetConversationsInFolder:
    def test_folder_lists_its_conversations(self, db):
        fid  = db.create_folder("Projet")
        cid1 = db.create_conversation(title="Conv 1")
        cid2 = db.create_conversation(title="Conv 2")
        db.move_conversation_to_folder(cid1, fid)
        db.move_conversation_to_folder(cid2, fid)
        ids = [c["id"] for c in db.get_conversations_in_folder(fid)]
        assert cid1 in ids and cid2 in ids

    def test_none_returns_unfiled_conversations(self, db):
        fid  = db.create_folder("Dossier")
        cid1 = db.create_conversation(title="Dans dossier")
        cid2 = db.create_conversation(title="Sans dossier")
        db.move_conversation_to_folder(cid1, fid)
        ids = [c["id"] for c in db.get_conversations_in_folder(None)]
        assert cid2 in ids
        assert cid1 not in ids

    def test_empty_folder_returns_empty_list(self, db):
        fid = db.create_folder("Vide")
        assert db.get_conversations_in_folder(fid) == []

    def test_folder_isolation(self, db):
        f1   = db.create_folder("F1")
        f2   = db.create_folder("F2")
        cid1 = db.create_conversation(title="Conv F1")
        cid2 = db.create_conversation(title="Conv F2")
        db.move_conversation_to_folder(cid1, f1)
        db.move_conversation_to_folder(cid2, f2)
        assert [c["id"] for c in db.get_conversations_in_folder(f1)] == [cid1]
        assert [c["id"] for c in db.get_conversations_in_folder(f2)] == [cid2]
