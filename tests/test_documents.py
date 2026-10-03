import hashlib

import pytest

from brain.documents import DocumentError, Documents


@pytest.fixture
def documents(brain_dir):
    return Documents(brain_dir)


@pytest.fixture
def invoice(tmp_path):
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF invoice")
    return path


def test_a_document_is_copied_into_its_folders_with_its_hash(documents, brain_dir, invoice):
    filed = documents.store(invoice, "car/2026-09-14 oil change invoice.pdf")

    target = brain_dir / "documents" / "car" / "2026-09-14 oil change invoice.pdf"
    assert target.read_bytes() == b"%PDF invoice"
    assert filed == {"path": "car/2026-09-14 oil change invoice.pdf", "sha256": hashlib.sha256(b"%PDF invoice").hexdigest()}
    assert invoice.exists()
    assert [p.name for p in target.parent.iterdir()] == [target.name]


def test_the_same_contents_filed_again_return_the_same_document(documents, invoice):
    first = documents.store(invoice, "car/invoice.pdf")

    assert documents.store(invoice, "car/invoice.pdf") == first


def test_other_contents_at_a_filed_path_are_refused(documents, brain_dir, invoice, tmp_path):
    documents.store(invoice, "car/invoice.pdf")
    other = tmp_path / "other.pdf"
    other.write_bytes(b"%PDF something else")

    with pytest.raises(DocumentError, match="already holds"):
        documents.store(other, "car/invoice.pdf")
    folder = brain_dir / "documents" / "car"
    assert (folder / "invoice.pdf").read_bytes() == b"%PDF invoice"
    assert [p.name for p in folder.iterdir()] == ["invoice.pdf"]


@pytest.mark.parametrize(
    "path",
    ["", "/car/invoice.pdf", "car//invoice.pdf", "../invoice.pdf", "car/./invoice.pdf", "car\\invoice.pdf",
     "C:/invoice.pdf", "car/invoice.pdf.", "car/invoice.pdf ", "car/what?.pdf", "car/con.txt", "car/"],
)
def test_a_path_that_is_not_a_plain_relative_one_is_refused(documents, brain_dir, invoice, path):
    with pytest.raises(DocumentError, match="relative|non-empty"):
        documents.store(invoice, path)
    assert not (brain_dir / "documents").exists()


def test_a_source_that_is_not_a_file_is_refused(documents, tmp_path):
    with pytest.raises(DocumentError, match="no file"):
        documents.store(tmp_path / "missing.pdf", "invoice.pdf")
    with pytest.raises(DocumentError, match="no file"):
        documents.store(tmp_path, "invoice.pdf")


def test_a_move_removes_the_original_once_the_document_is_filed(documents, brain_dir, invoice):
    filed = documents.store(invoice, "assets/car/invoice.pdf", move=True)

    assert (brain_dir / "documents" / "assets" / "car" / "invoice.pdf").read_bytes() == b"%PDF invoice"
    assert filed["sha256"] == hashlib.sha256(b"%PDF invoice").hexdigest()
    assert not invoice.exists()


def test_a_document_already_filed_is_never_moved(documents, brain_dir, invoice):
    documents.store(invoice, "car/invoice.pdf")
    filed = brain_dir / "documents" / "car" / "invoice.pdf"

    with pytest.raises(DocumentError, match="never moved"):
        documents.store(filed, "car/elsewhere.pdf", move=True)
    assert filed.exists()
    assert not (brain_dir / "documents" / "car" / "elsewhere.pdf").exists()


def test_an_original_that_cannot_be_removed_is_filed_and_reported(documents, brain_dir, invoice, monkeypatch):
    unlink = type(invoice).unlink

    def refuse(path, missing_ok=False):
        if path == invoice:
            raise PermissionError(13, "Permission denied")
        unlink(path, missing_ok)

    monkeypatch.setattr(type(invoice), "unlink", refuse)
    with pytest.raises(DocumentError, match="could not be removed") as refused:
        documents.store(invoice, "car/invoice.pdf", move=True)

    assert hashlib.sha256(b"%PDF invoice").hexdigest() in str(refused.value)
    assert (brain_dir / "documents" / "car" / "invoice.pdf").read_bytes() == b"%PDF invoice"
    assert invoice.exists()


def test_contents_an_entry_already_names_are_refused_wherever_they_would_go(brain_dir, reader, entries, invoice):
    documents = Documents(brain_dir, reader)
    filed = documents.store(invoice, "car/invoice.pdf")
    entry_id = entries.write_journal(
        event_date="2026-09-14", description="Oil change invoice", body="Filed.", documents=[filed],
    )

    with pytest.raises(DocumentError, match="already filed at 'car/invoice.pdf'") as refused:
        documents.store(invoice, "car/another.pdf", move=True)

    assert entry_id in str(refused.value)
    assert invoice.exists()
    assert sorted(p.name for p in (brain_dir / "documents" / "car").iterdir()) == ["invoice.pdf"]


def test_filing_again_before_an_entry_names_it_returns_it_as_it_is(brain_dir, reader, invoice):
    documents = Documents(brain_dir, reader)
    first = documents.store(invoice, "car/invoice.pdf")

    assert documents.store(invoice, "car/invoice.pdf", move=True) == first
    assert not invoice.exists()


def test_browsing_lists_one_folder_with_how_many_documents_each_holds(documents, brain_dir, invoice, tmp_path):
    assert documents.browse() == {"folders": [], "documents": []}
    documents.store(invoice, "assets/car/service/2026-09-14-invoice.pdf")
    documents.store(invoice, "assets/car/2026-01-02-title.pdf")
    documents.store(invoice, "assets/House/deed.pdf")
    (brain_dir / "documents" / "assets" / ".copy.tmp").write_bytes(b"part")
    (brain_dir / "documents" / "assets" / "notes.txt").write_bytes(b"notes")

    assert documents.browse() == {"folders": [{"name": "assets", "documents": 4}], "documents": []}
    assert documents.browse("assets") == {
        "folders": [{"name": "car", "documents": 2}, {"name": "House", "documents": 1}],
        "documents": ["notes.txt"],
    }
    assert documents.browse("assets/car") == {
        "folders": [{"name": "service", "documents": 1}], "documents": ["2026-01-02-title.pdf"],
    }
    with pytest.raises(DocumentError, match="no folder"):
        documents.browse("assets/boat")
    with pytest.raises(DocumentError, match="relative"):
        documents.browse("../assets")
