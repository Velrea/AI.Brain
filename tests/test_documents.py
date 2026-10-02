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
