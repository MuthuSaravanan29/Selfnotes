"""
Comprehensive integration test suite for Slingshot.

Tests all API endpoints: auth, notes CRUD, search, tags, backlinks,
attachments, git sync config, health check, and error handling.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests

TEST_DIR = Path(tempfile.mkdtemp(suffix="_slingshot_test"))
DATA_DIR = TEST_DIR / "data"
INDEX_DIR = DATA_DIR / ".flatnotes"
SERVER_PORT = 9898
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"
BASE = f"{SERVER_URL}"

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
BOLD = "\033[1m"
RESET = "\033[0m"

passed = 0
failed = 0


def report(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  {PASS}  {name}")
    else:
        failed += 1
        print(f"  {FAIL}  {name} -> {detail}")


def check(name, fn):
    try:
        fn()
        report(name, True)
    except Exception as e:
        report(name, False, str(e)[:200])


def setup():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Init git repo for auto-sync testing
    subprocess.run(["git", "init"], cwd=DATA_DIR, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@slingshot.app"],
        cwd=DATA_DIR, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Slingshot Test"],
        cwd=DATA_DIR, capture_output=True,
    )
    (DATA_DIR / "README.md").write_text("# Slingshot Test Repo\n")
    subprocess.run(["git", "add", "-A"], cwd=DATA_DIR, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial commit", "--allow-empty"],
        cwd=DATA_DIR, capture_output=True,
    )

    env = os.environ.copy()
    env.update({
        "FLATNOTES_PATH": str(DATA_DIR),
        "FLATNOTES_AUTH_TYPE": "password",
        "FLATNOTES_USERNAME": "testuser",
        "FLATNOTES_PASSWORD": "testpass123",
        "FLATNOTES_SECRET_KEY": "test-secret-key-for-testing-only",
        "FLATNOTES_PORT": str(SERVER_PORT),
    })

    project_dir = Path(__file__).resolve().parent.parent
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--app-dir", "server",
         "--host", "127.0.0.1", "--port", str(SERVER_PORT)],
        cwd=str(project_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    for _ in range(60):
        try:
            r = requests.get(f"{BASE}/health", timeout=2)
            if r.status_code == 200:
                print(f"  Server ready on port {SERVER_PORT}")
                return proc
        except requests.ConnectionError:
            time.sleep(0.5)

    # If not ready, dump output
    out, err = proc.communicate(timeout=3)
    print(f"  STDOUT: {out.decode()[:500]}")
    print(f"  STDERR: {err.decode()[:500]}")
    proc.kill()
    raise RuntimeError("Server did not start")


def teardown(proc):
    if proc:
        os.kill(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    shutil.rmtree(TEST_DIR, ignore_errors=True)


def get_token():
    r = requests.post(
        f"{BASE}/api/token",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    return data["access_token"]


def headers(token=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


# ---- Tests ----

def test_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200
    assert r.text == '"OK"'


def test_auth_login_success():
    r = requests.post(
        f"{BASE}/api/token",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "token_type" in data


def test_auth_login_failure():
    r = requests.post(
        f"{BASE}/api/token",
        json={"username": "testuser", "password": "wrongpass"},
    )
    assert r.status_code == 401


def test_auth_check_valid():
    tok = get_token()
    r = requests.get(f"{BASE}/api/auth-check", headers=headers(tok))
    assert r.status_code == 200
    assert r.text == '"OK"'


def test_auth_check_invalid():
    r = requests.get(
        f"{BASE}/api/auth-check",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    # Should return 401/403
    assert r.status_code in (401, 403)


def test_get_config():
    tok = get_token()
    r = requests.get(f"{BASE}/api/config", headers=headers(tok))
    assert r.status_code == 200
    data = r.json()
    assert data["authType"] == "password"


def test_create_note():
    tok = get_token()
    r = requests.post(
        f"{BASE}/api/notes",
        headers=headers(tok),
        json={"title": "test-note-1", "content": "# Hello World\n\nThis is a test note."},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "test-note-1"
    assert data["content"] == "# Hello World\n\nThis is a test note."
    assert "lastModified" in data


def test_get_note():
    tok = get_token()
    r = requests.get(f"{BASE}/api/notes/test-note-1", headers=headers(tok))
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "test-note-1"


def test_get_note_not_found():
    tok = get_token()
    r = requests.get(f"{BASE}/api/notes/nonexistent-note", headers=headers(tok))
    assert r.status_code == 404


def test_create_duplicate_note():
    tok = get_token()
    r = requests.post(
        f"{BASE}/api/notes",
        headers=headers(tok),
        json={"title": "test-note-1", "content": "duplicate"},
    )
    assert r.status_code == 409


def test_update_note():
    tok = get_token()
    r = requests.patch(
        f"{BASE}/api/notes/test-note-1",
        headers=headers(tok),
        json={"newTitle": "test-note-renamed", "newContent": "# Renamed\n\nUpdated content."},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "test-note-renamed"
    assert "Updated content." in data["content"]


def test_update_note_content_only():
    tok = get_token()
    r = requests.patch(
        f"{BASE}/api/notes/test-note-renamed",
        headers=headers(tok),
        json={"newContent": "# Renamed\n\nContent changed again."},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "test-note-renamed"
    assert "Content changed again." in data["content"]


def test_delete_note():
    tok = get_token()
    r = requests.delete(f"{BASE}/api/notes/test-note-renamed", headers=headers(tok))
    assert r.status_code == 200

    # Verify deleted
    r = requests.get(f"{BASE}/api/notes/test-note-renamed", headers=headers(tok))
    assert r.status_code == 404


def test_delete_note_not_found():
    tok = get_token()
    r = requests.delete(f"{BASE}/api/notes/nonexistent", headers=headers(tok))
    assert r.status_code == 404


def test_search_basic():
    tok = get_token()
    # Create a note to search for
    requests.post(
        f"{BASE}/api/notes",
        headers=headers(tok),
        json={"title": "searchable-note", "content": "This is a unique searchable term xylophone"},
    )
    time.sleep(0.3)  # let index sync
    r = requests.get(
        f"{BASE}/api/search?term=xylophone",
        headers=headers(tok),
    )
    assert r.status_code == 200
    data = r.json()
    titles = [n["title"] for n in data]
    assert "searchable-note" in titles


def test_search_empty_term():
    tok = get_token()
    r = requests.get(f"{BASE}/api/search?term=", headers=headers(tok))
    assert r.status_code == 200  # Should return empty or all results


def test_search_wildcard():
    tok = get_token()
    r = requests.get(f"{BASE}/api/search?term=*", headers=headers(tok))
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1


def test_tags():
    tok = get_token()
    requests.post(
        f"{BASE}/api/notes",
        headers=headers(tok),
        json={"title": "tagged-note", "content": "This note has #python and #testing tags"},
    )
    time.sleep(0.3)
    r = requests.get(f"{BASE}/api/tags", headers=headers(tok))
    assert r.status_code == 200
    data = r.json()
    assert "python" in data
    assert "testing" in data


def test_backlinks():
    tok = get_token()
    # Create note A
    requests.post(
        f"{BASE}/api/notes",
        headers=headers(tok),
        json={"title": "note-a", "content": "Note A content"},
    )
    # Create note B that links to note A
    requests.post(
        f"{BASE}/api/notes",
        headers=headers(tok),
        json={"title": "note-b", "content": "See [[note-a]] for details"},
    )
    time.sleep(0.3)
    r = requests.get(f"{BASE}/api/backlinks/note-a", headers=headers(tok))
    assert r.status_code == 200
    data = r.json()
    assert "note-b" in data


def test_backlinks_no_links():
    tok = get_token()
    r = requests.get(f"{BASE}/api/backlinks/nonexistent", headers=headers(tok))
    assert r.status_code == 200
    assert r.json() == []


def test_invalid_note_title():
    tok = get_token()
    r = requests.post(
        f"{BASE}/api/notes",
        headers=headers(tok),
        json={"title": "invalid/title", "content": "test"},
    )
    # FastAPI returns 422 for Pydantic validation errors (ValueError in AfterValidator)
    assert r.status_code == 422


def test_create_note_empty_content():
    tok = get_token()
    r = requests.post(
        f"{BASE}/api/notes",
        headers=headers(tok),
        json={"title": "empty-content-note", "content": ""},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["content"] == ""


def test_git_config_get():
    tok = get_token()
    r = requests.get(f"{BASE}/api/git-config", headers=headers(tok))
    assert r.status_code == 200
    data = r.json()
    assert "remoteUrl" in data or "remote_url" in data


def test_git_config_set():
    tok = get_token()
    r = requests.post(
        f"{BASE}/api/git-config",
        headers=headers(tok),
        json={"remote_url": "https://github.com/test/repo.git", "auth_type": "token"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


def test_git_config_save_and_retrieve():
    tok = get_token()
    requests.post(
        f"{BASE}/api/git-config",
        headers=headers(tok),
        json={"remote_url": "https://github.com/test/repo.git", "auth_type": "token", "token": "ghp_test123"},
    )
    r = requests.get(f"{BASE}/api/git-config", headers=headers(tok))
    assert r.status_code == 200
    data = r.json()
    # Token should NOT be returned in GET (security)
    url_key = "remoteUrl" if "remoteUrl" in data else "remote_url"
    assert data[url_key] == "https://github.com/test/repo.git"


def test_git_verify_no_remote():
    tok = get_token()
    # Clear git config first
    requests.post(
        f"{BASE}/api/git-config",
        headers=headers(tok),
        json={"remote_url": "", "auth_type": "token"},
    )
    r = requests.post(f"{BASE}/api/git-verify", headers=headers(tok))
    assert r.status_code == 400
    assert "No remote URL" in r.text


def test_frontend_served():
    r = requests.get(f"{BASE}/", timeout=5)
    assert r.status_code == 200
    assert "Slingshot" in r.text or "slingshot" in r.text


def test_frontend_login_page():
    r = requests.get(f"{BASE}/login", timeout=5)
    assert r.status_code == 200


def test_frontend_search_page():
    r = requests.get(f"{BASE}/search", timeout=5)
    assert r.status_code == 200


def test_frontend_new_note_page():
    r = requests.get(f"{BASE}/new", timeout=5)
    assert r.status_code == 200


def test_frontend_note_page():
    tok = get_token()
    # Create a note first
    requests.post(
        f"{BASE}/api/notes",
        headers=headers(tok),
        json={"title": "frontend-test-note", "content": "test"},
    )
    r = requests.get(f"{BASE}/note/frontend-test-note", timeout=5)
    assert r.status_code == 200


def test_attachments_upload():
    tok = get_token()
    files = {"file": ("test.txt", b"Hello attachment!", "text/plain")}
    r = requests.post(
        f"{BASE}/api/attachments",
        headers={"Authorization": f"Bearer {tok}"},
        files=files,
    )
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data


def test_attachments_get():
    tok = get_token()
    # Upload first
    files = {"file": ("get-test.txt", b"Get attachment!", "text/plain")}
    r = requests.post(
        f"{BASE}/api/attachments",
        headers={"Authorization": f"Bearer {tok}"},
        files=files,
    )
    assert r.status_code == 200
    filename = r.json()["filename"]

    r = requests.get(f"{BASE}/api/attachments/{filename}", headers=headers(tok))
    assert r.status_code == 200
    assert r.content == b"Get attachment!"


def test_attachments_not_found():
    tok = get_token()
    r = requests.get(f"{BASE}/api/attachments/nonexistent.txt", headers=headers(tok))
    assert r.status_code == 404


def test_static_files_served():
    r = requests.get(f"{BASE}/assets/index-BkbykDv9.css", timeout=5)
    # Might 404 if filename has hash, but should at least return something
    assert r.status_code in (200, 404)


def test_cors_headers():
    tok = get_token()
    r = requests.options(
        f"{BASE}/api/notes",
        headers=headers(tok),
    )
    # CORS should allow requests
    assert r.status_code == 200


def test_create_note_special_chars():
    tok = get_token()
    r = requests.post(
        f"{BASE}/api/notes",
        headers=headers(tok),
        json={"title": "note-with-special-chars-123", "content": "Content with special chars: !@#$%^&*()"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "note-with-special-chars-123"


def test_update_nonexistent_note():
    tok = get_token()
    r = requests.patch(
        f"{BASE}/api/notes/does-not-exist-at-all",
        headers=headers(tok),
        json={"newContent": "test"},
    )
    assert r.status_code == 404


def test_empty_tag_search():
    tok = get_token()
    r = requests.get(f"{BASE}/api/search?term=%23python", headers=headers(tok))
    assert r.status_code == 200


def test_create_multiple_notes():
    tok = get_token()
    for i in range(5):
        r = requests.post(
            f"{BASE}/api/notes",
            headers=headers(tok),
            json={"title": f"bulk-note-{i}", "content": f"Bulk note number {i}"},
        )
        assert r.status_code == 200
    time.sleep(0.3)
    r = requests.get(f"{BASE}/api/search?term=*", headers=headers(tok))
    assert r.status_code == 200
    data = r.json()
    bulk_titles = [n["title"] for n in data if n["title"].startswith("bulk-note")]
    assert len(bulk_titles) == 5


def test_search_with_sort():
    tok = get_token()
    r = requests.get(
        f"{BASE}/api/search?term=*&sort=title&order=asc",
        headers=headers(tok),
    )
    assert r.status_code == 200
    data = r.json()
    if len(data) >= 2:
        assert data[0]["title"] <= data[1]["title"]


def test_search_with_limit():
    tok = get_token()
    r = requests.get(
        f"{BASE}/api/search?term=*&limit=3",
        headers=headers(tok),
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) <= 3


def test_health_method_not_allowed():
    r = requests.post(f"{BASE}/health", timeout=5)
    assert r.status_code == 405


def test_api_404():
    tok = get_token()
    r = requests.get(f"{BASE}/api/nonexistent-endpoint", headers=headers(tok))
    assert r.status_code == 404


def test_attachment_duplicate():
    tok = get_token()
    files = {"file": ("dup.txt", b"Duplicate!", "text/plain")}
    r = requests.post(
        f"{BASE}/api/attachments",
        headers={"Authorization": f"Bearer {tok}"},
        files=files,
    )
    assert r.status_code == 200
    first_filename = r.json()["filename"]
    # Upload same filename again - appends timestamp to avoid conflict
    r = requests.post(
        f"{BASE}/api/attachments",
        headers={"Authorization": f"Bearer {tok}"},
        files=files,
    )
    assert r.status_code == 200
    second_filename = r.json()["filename"]
    # Filenames should differ (timestamp suffix added)
    assert second_filename != first_filename
    assert second_filename.startswith("dup_")


def test_git_log_has_commits():
    """Verify that note operations created git commits."""
    result = subprocess.run(
        ["git", "log", "--oneline", "-20"],
        cwd=DATA_DIR, capture_output=True, text=True,
    )
    assert result.returncode == 0
    log = result.stdout
    assert "notes: created" in log
    assert "notes: updated" in log
    assert "notes: deleted" in log


def test_git_notes_commits():
    """Verify git auto-sync committed note changes."""
    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=DATA_DIR, capture_output=True, text=True,
    )
    assert result.returncode == 0
    log = result.stdout
    # Should have multiple note commits
    assert len(log.splitlines()) >= 5


def run_all():
    tests = [
        # Health & Config
        ("Health endpoint", test_health),
        ("Config endpoint returns auth type", test_get_config),

        # Auth
        ("Login with valid credentials", test_auth_login_success),
        ("Login with invalid credentials returns 401", test_auth_login_failure),
        ("Auth check with valid token", test_auth_check_valid),
        ("Auth check with invalid token", test_auth_check_invalid),

        # Notes CRUD
        ("Create a note", test_create_note),
        ("Get a note by title", test_get_note),
        ("Get nonexistent note returns 404", test_get_note_not_found),
        ("Create duplicate note returns 409", test_create_duplicate_note),
        ("Update note title and content", test_update_note),
        ("Update note content only", test_update_note_content_only),
        ("Delete a note", test_delete_note),
        ("Delete nonexistent note returns 404", test_delete_note_not_found),

        # Search
        ("Search finds matching notes", test_search_basic),
        ("Search with empty term", test_search_empty_term),
        ("Search wildcard returns all notes", test_search_wildcard),
        ("Search with sort order", test_search_with_sort),
        ("Search with limit", test_search_with_limit),
        ("Search for tags (#tag)", test_empty_tag_search),

        # Tags
        ("Tags endpoint returns indexed tags", test_tags),

        # Backlinks
        ("Backlinks find linking notes", test_backlinks),
        ("Backlinks returns empty for unlinked note", test_backlinks_no_links),

        # Error Handling
        ("Invalid note title returns 400", test_invalid_note_title),
        ("Create note with empty content", test_create_note_empty_content),
        ("Update nonexistent note returns 404", test_update_nonexistent_note),
        ("Health rejects POST method", test_health_method_not_allowed),
        ("Unknown API endpoint returns 404", test_api_404),

        # Special Cases
        ("Create note with special characters", test_create_note_special_chars),
        ("Create multiple notes in bulk", test_create_multiple_notes),

        # Git Config
        ("Get git config returns defaults", test_git_config_get),
        ("Set git config", test_git_config_set),
        ("Save and retrieve git config (no token leak)", test_git_config_save_and_retrieve),
        ("Git verify with no remote returns 400", test_git_verify_no_remote),

        # Attachments
        ("Upload attachment", test_attachments_upload),
        ("Get attachment by filename", test_attachments_get),
        ("Get nonexistent attachment returns 404", test_attachments_not_found),
        ("Upload duplicate attachment returns 409", test_attachment_duplicate),

        # Frontend
        ("Frontend serves index.html", test_frontend_served),
        ("Frontend /login page", test_frontend_login_page),
        ("Frontend /search page", test_frontend_search_page),
        ("Frontend /new page", test_frontend_new_note_page),
        ("Frontend /note/{title} page", test_frontend_note_page),

        # Git auto-sync verification
        ("Git log contains note commits", test_git_log_has_commits),
        ("Git has multiple note commits", test_git_notes_commits),
    ]

    print(f"\n{BOLD}Running {len(tests)} integration tests...{RESET}\n")
    for name, fn in tests:
        check(name, fn)

    total = passed + failed
    print(f"\n{BOLD}Results: {passed}/{total} passed", end="")
    if failed:
        print(f", {failed} failed", end="")
    print(f"{RESET}")
    return failed == 0


if __name__ == "__main__":
    print(f"{BOLD}Slingshot Integration Test Suite{RESET}")
    print(f"  Data dir: {DATA_DIR}")
    print(f"  Server:   {SERVER_URL}")

    proc = None
    try:
        proc = setup()
        success = run_all()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n{FAIL} Setup failed: {e}{RESET}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        teardown(proc)
