"""Almacenamiento en Firestore con un cliente falso en memoria (Fase 2, I4).

La suite principal no usa red ni el SDK real; el cliente falso imita solo la
parte de la API de google-cloud-firestore que usan las clases."""

from datetime import datetime


class _Snap:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data)


class _Doc:
    def __init__(self, col, doc_id):
        self._col, self.id = col, doc_id

    def get(self, transaction=None):
        return _Snap(self._col.docs.get(self.id))

    def set(self, data):
        self._col.docs[self.id] = dict(data)


class _Query:
    def __init__(self, docs):
        self._docs = docs

    def stream(self):
        return [_Snap(d) for d in self._docs]


class _Col:
    def __init__(self):
        self.docs = {}

    def document(self, doc_id):
        return _Doc(self, doc_id)

    def limit(self, n):
        return _Query(list(self.docs.values())[:n])

    def where(self, field, op, value):
        assert op == "=="
        return _Query([d for d in self.docs.values() if d.get(field) == value])


class _Client:
    def __init__(self):
        self.cols = {}

    def collection(self, name):
        return self.cols.setdefault(name, _Col())


class _Txn:
    def __init__(self):
        self.writes = []

    def set(self, ref, data):
        self.writes.append(data)
        ref.set(data)


def _run_in_fake_txn(fn):
    return fn(_Txn())


def test_conversation_store_conforms_and_roundtrips(coordinator):
    from backend.core.firestore_store import FirestoreConversationStore
    from backend.core.storage import ConversationStorage

    client = _Client()
    store = FirestoreConversationStore(client=client)
    assert isinstance(store, ConversationStorage)

    conv = coordinator.handle("Quiero una laptop nueva", caller="Carlos Carballo")
    store.update(conv)
    stored = client.cols["conversations"].docs[conv.id]
    assert isinstance(stored["expire_at"], datetime)  # política TTL de Firestore

    restored = store.get(conv.id)
    assert restored.to_dict() == conv.to_dict()
    assert store.get("no-existe") is None


def test_conversation_store_create_and_list_sorted():
    from backend.core.firestore_store import FirestoreConversationStore

    store = FirestoreConversationStore(client=_Client())
    first = store.create("uno")
    second = store.create("dos")
    assert [c.id for c in store.list()] == [first.id, second.id]


def test_approval_store_transactional_decide():
    from backend.core.approvals import APPROVED, ApprovalRequest, ApprovalStorage
    from backend.core.firestore_store import FirestoreApprovalStore

    store = FirestoreApprovalStore(client=_Client(), transactional=_run_in_fake_txn)
    assert isinstance(store, ApprovalStorage)
    a = store.create(ApprovalRequest(conversation_id="c", action="a", resource="r", manager="m"))
    assert [p.id for p in store.list_pending()] == [a.id]

    approval, changed = store.decide(a.id, "approved", "m", "ok")
    assert changed and approval.status == APPROVED
    assert store.get(a.id).status == APPROVED
    assert store.list_pending() == []

    _, changed_again = store.decide(a.id, "rejected", "otro")
    assert not changed_again and store.get(a.id).decided_by == "m"
    assert store.decide("nope", "approved", "x") == (None, False)
