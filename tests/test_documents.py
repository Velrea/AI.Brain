import hashlib
import json
import subprocess
import sys

import pytest

from brain.read import CEILING
from documents import DocumentError, Documents, main

from conftest import PLUGIN, create


@pytest.fixture
def documents(brain_dir):
    brain_dir.mkdir()
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


@pytest.mark.parametrize("move", [True, False])
@pytest.mark.parametrize("path", ["car/invoice.pdf", "car/elsewhere.pdf"])
def test_a_document_already_filed_is_never_filed_again(documents, brain_dir, invoice, move, path):
    documents.store(invoice, "car/invoice.pdf")
    filed = brain_dir / "documents" / "car" / "invoice.pdf"
    filed.write_bytes(b"%PDF invoice, edited")

    with pytest.raises(DocumentError, match="at 'car/invoice.pdf', and is never filed again: check it"):
        documents.store(filed, path, move=move)
    assert filed.read_bytes() == b"%PDF invoice, edited"
    assert [p.name for p in filed.parent.iterdir()] == ["invoice.pdf"]


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


def test_contents_a_document_entry_names_are_refused_wherever_they_would_go(brain_dir, reader, writer, invoice):
    brain_dir.mkdir()
    documents = Documents(brain_dir, reader)
    filed = documents.store(invoice, "car/invoice.pdf")
    entry_id = create(writer, "oil-change-invoice", type="document", description="Oil change invoice",
                      details=filed)

    with pytest.raises(DocumentError, match="already filed at 'car/invoice.pdf'") as refused:
        documents.store(invoice, "car/another.pdf", move=True)

    assert entry_id in str(refused.value)
    assert invoice.exists()
    assert sorted(p.name for p in (brain_dir / "documents" / "car").iterdir()) == ["invoice.pdf"]


def test_filing_again_before_an_entry_names_it_returns_it_as_it_is(brain_dir, reader, invoice):
    brain_dir.mkdir()
    documents = Documents(brain_dir, reader)
    first = documents.store(invoice, "car/invoice.pdf")

    assert documents.store(invoice, "car/invoice.pdf", move=True) == first
    assert not invoice.exists()


def test_a_brain_folder_that_does_not_exist_is_refused(tmp_path):
    with pytest.raises(DocumentError, match="does not exist"):
        Documents(tmp_path / "unmounted")


def test_the_script_prints_one_json_object_or_says_what_went_wrong(brain_dir, data_dir, writer, invoice, capsys):
    brain_dir.mkdir()
    digest = hashlib.sha256(b"%PDF invoice").hexdigest()
    store = ["store", "--brain", str(brain_dir), "--data", str(data_dir), str(invoice)]

    assert main([*store, "car/invoice.pdf"]) == 0
    filed = json.loads(capsys.readouterr().out)
    assert filed == {"path": "car/invoice.pdf", "sha256": digest}
    assert main(["list", "--brain", str(brain_dir)]) == 0
    assert json.loads(capsys.readouterr().out) == {"folders": [{"name": "car", "documents": 1}], "documents": []}

    # Recorded by the entries this machine's server writes, through the same plugin data folder.
    create(writer, "oil-change-invoice", type="document", details=filed)
    assert main([*store, "car/copy.pdf", "--move"]) == 1
    printed = capsys.readouterr()
    assert printed.out == "" and "already filed" in printed.err
    assert invoice.exists()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def checked(brain_dir, reader, writer):
    """A Documents that checks, and a function filing bytes at a path and
    recording them as a document entry, returning the entry's id."""
    brain_dir.mkdir()
    documents = Documents(brain_dir, reader)

    def record(path: str, data: bytes, event_date: str = "2026-01-01") -> str:
        file = brain_dir / "documents" / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
        return create(writer, f"document-{sha(path.encode())[:8]}", type="document", event_date=event_date,
                      details={"path": path, "sha256": sha(data)})

    return documents, record


NOTHING = {"changed": [], "moved": [], "missing": [], "unrecorded": []}


def test_documents_as_recorded_check_clean(checked):
    documents, record = checked
    assert documents.check() == NOTHING
    record("car/invoice.pdf", b"%PDF invoice")
    record("house/deed.pdf", b"%PDF deed")

    assert documents.check() == NOTHING


def test_checking_finds_each_way_a_document_differs_from_its_entry(checked, brain_dir):
    documents, record = checked
    edited = record("work/prep-sheet.txt", b"Agenda: one")
    moved = record("car/invoice.pdf", b"%PDF invoice")
    deleted = record("car/old-title.pdf", b"%PDF title")
    record("house/deed.pdf", b"%PDF deed")
    root = brain_dir / "documents"
    (root / "work" / "prep-sheet.txt").write_bytes(b"Agenda: one, two")
    (root / "car" / "invoice.pdf").rename(root / "car" / "2026-09-14-invoice.pdf")
    (root / "car" / "old-title.pdf").unlink()
    (root / "house" / "survey.pdf").write_bytes(b"%PDF survey")
    (root / "house" / ".survey.pdf.0a1b.tmp").write_bytes(b"part")

    assert documents.check() == {
        "changed": [{"path": "work/prep-sheet.txt", "entry": edited, "sha256": sha(b"Agenda: one, two")}],
        "moved": [{"entry": moved, "from": "car/invoice.pdf", "to": "car/2026-09-14-invoice.pdf"}],
        "missing": [{"path": "car/old-title.pdf", "entry": deleted}],
        "unrecorded": [{"path": "house/survey.pdf", "sha256": sha(b"%PDF survey")}],
    }


def test_checking_a_folder_or_a_document_checks_only_it(checked, brain_dir):
    documents, record = checked
    edited = record("car/invoice.pdf", b"%PDF invoice")
    record("cart/manual.pdf", b"%PDF manual")
    deed = record("house/deed.pdf", b"%PDF deed")
    root = brain_dir / "documents"
    (root / "car" / "invoice.pdf").write_bytes(b"%PDF invoice, paid")
    (root / "cart" / "manual.pdf").write_bytes(b"%PDF manual, revised")
    (root / "house" / "deed.pdf").unlink()
    change = {"path": "car/invoice.pdf", "entry": edited, "sha256": sha(b"%PDF invoice, paid")}

    assert documents.check("car") == NOTHING | {"changed": [change]}
    assert documents.check("car/invoice.pdf") == NOTHING | {"changed": [change]}
    assert documents.check("house/deed.pdf") == NOTHING | {"missing": [{"path": "house/deed.pdf", "entry": deed}]}
    with pytest.raises(DocumentError, match="nothing is filed at 'boat'"):
        documents.check("boat")
    with pytest.raises(DocumentError, match="relative"):
        documents.check("../car")


def test_checking_reads_past_the_search_ceiling(checked):
    documents, record = checked
    for number in range(CEILING + 1):
        record(f"receipts/{number:03}.txt", f"Receipt {number}".encode(), f"2026-{number % 12 + 1:02}-01")

    assert documents.check() == NOTHING


def test_more_entries_on_one_date_than_a_search_returns_cannot_be_checked(checked):
    documents, record = checked
    for number in range(CEILING + 1):
        record(f"receipts/{number:03}.txt", f"Receipt {number}".encode())

    with pytest.raises(DocumentError, match=f"{CEILING + 1} document entries share the event date 2026-01-01"):
        documents.check()


def test_checking_needs_the_entries(documents):
    with pytest.raises(DocumentError, match="needs the recorded entries"):
        documents.check()


def test_the_script_checks_through_the_same_index(brain_dir, data_dir, checked, capsys):
    documents, record = checked
    record("car/invoice.pdf", b"%PDF invoice")
    (brain_dir / "documents" / "car" / "invoice.pdf").write_bytes(b"%PDF invoice, paid")

    assert main(["check", "--brain", str(brain_dir), "--data", str(data_dir), "car"]) == 0
    assert json.loads(capsys.readouterr().out)["changed"][0]["sha256"] == sha(b"%PDF invoice, paid")


def test_the_launcher_runs_the_script_on_this_machines_python(brain_dir, invoice):
    brain_dir.mkdir()
    script = PLUGIN / "skills" / "document" / "scripts" / "documents.py"
    if sys.platform == "win32":
        command = ["cmd", "/c", str(PLUGIN / "scripts" / "brain.cmd")]
    else:
        command = ["sh", str(PLUGIN / "scripts" / "brain")]

    done = subprocess.run([*command, "run", str(script), "list", "--brain", str(brain_dir)],
                          capture_output=True, text=True)

    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {"folders": [], "documents": []}


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
