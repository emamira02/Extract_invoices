from invoice_extractor.storage import HistoryStore


def test_history_keeps_only_the_latest_entries_per_user(tmp_path):
    store = HistoryStore(tmp_path / "h.db", limit=2)
    for i in range(3):
        store.add("alice@example.com", f"invoice_{i}.pdf", {"n": i}, b"%PDF-1.7")
    store.add("bob@example.com", "bob.pdf", {"n": 99}, None)

    alice = store.list("alice@example.com")
    assert [r["file_name"] for r in alice] == ["invoice_2.pdf", "invoice_1.pdf"]
    assert store.get("alice@example.com", alice[0]["id"]) == ({"n": 2}, b"%PDF-1.7")

    # users never see each other's analyses
    assert store.get("bob@example.com", alice[0]["id"]) is None
    assert [r["file_name"] for r in store.list("alice@example.com", search="_1")] == ["invoice_1.pdf"]

    store.clear("alice@example.com")
    assert store.list("alice@example.com") == []
    assert len(store.list("bob@example.com")) == 1
