import json
import os
import subprocess
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import api_messages
from attachments.base import BaseAttachments
from attachments.models import AttachmentCreateResponse
from auth.base import BaseAuth
from auth.models import Login, Token
from global_config import AuthType, GlobalConfig, GlobalConfigResponseModel
from helpers import get_env, replace_base_href
from notes.base import BaseNotes
from notes.models import Note, NoteCreate, NoteUpdate, SearchResult

global_config = GlobalConfig()
auth: BaseAuth = global_config.load_auth()
note_storage: BaseNotes = global_config.load_note_storage()
attachment_storage: BaseAttachments = global_config.load_attachment_storage()
auth_deps = [Depends(auth.authenticate)] if auth else []
router = APIRouter()
app = FastAPI(
    docs_url=global_config.path_prefix + "/docs",
    openapi_url=global_config.path_prefix + "/openapi.json",
)
replace_base_href("client/dist/index.html", global_config.path_prefix)


# region UI
@router.get("/", include_in_schema=False)
@router.get("/login", include_in_schema=False)
@router.get("/search", include_in_schema=False)
@router.get("/new", include_in_schema=False)
@router.get("/note/{title}", include_in_schema=False)
def root(title: str = ""):
    with open("client/dist/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)


# endregion


# region Auth
if global_config.auth_type not in [AuthType.NONE, AuthType.READ_ONLY]:

    @router.post("/api/token", response_model=Token)
    def token(data: Login):
        try:
            return auth.login(data)
        except ValueError:
            raise HTTPException(
                status_code=401, detail=api_messages.login_failed
            )


@router.get("/api/auth-check", dependencies=auth_deps)
def auth_check() -> str:
    """A lightweight endpoint that simply returns 'OK' if the user is
    authenticated."""
    return "OK"


# endregion


# region Notes
# Get Note
@router.get(
    "/api/notes/{title}",
    dependencies=auth_deps,
    response_model=Note,
)
def get_note(title: str):
    """Get a specific note."""
    try:
        return note_storage.get(title)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=api_messages.invalid_note_title
        )
    except FileNotFoundError:
        raise HTTPException(404, api_messages.note_not_found)


if global_config.auth_type != AuthType.READ_ONLY:

    # Create Note
    @router.post(
        "/api/notes",
        dependencies=auth_deps,
        response_model=Note,
    )
    def post_note(note: NoteCreate):
        """Create a new note."""
        try:
            return note_storage.create(note)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileExistsError:
            raise HTTPException(
                status_code=409, detail=api_messages.note_exists
            )

    # Update Note
    @router.patch(
        "/api/notes/{title}",
        dependencies=auth_deps,
        response_model=Note,
    )
    def patch_note(title: str, data: NoteUpdate):
        try:
            return note_storage.update(title, data)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileExistsError:
            raise HTTPException(
                status_code=409, detail=api_messages.note_exists
            )
        except FileNotFoundError:
            raise HTTPException(404, api_messages.note_not_found)

    # Delete Note
    @router.delete(
        "/api/notes/{title}",
        dependencies=auth_deps,
        response_model=None,
    )
    def delete_note(title: str):
        try:
            note_storage.delete(title)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileNotFoundError:
            raise HTTPException(404, api_messages.note_not_found)


# endregion


# region Search
@router.get(
    "/api/search",
    dependencies=auth_deps,
    response_model=List[SearchResult],
)
def search(
    term: str,
    sort: Literal["score", "title", "lastModified"] = "score",
    order: Literal["asc", "desc"] = "desc",
    limit: int = None,
):
    """Perform a full text search on all notes."""
    if sort == "lastModified":
        sort = "last_modified"
    return note_storage.search(term, sort=sort, order=order, limit=limit)


@router.get(
    "/api/tags",
    dependencies=auth_deps,
    response_model=List[str],
)
def get_tags():
    """Get a list of all indexed tags."""
    return note_storage.get_tags()


@router.get(
    "/api/backlinks/{title}",
    dependencies=auth_deps,
    response_model=List[str],
)
def get_backlinks(title: str):
    """Get a list of note titles that link to the given title."""
    return note_storage.get_backlinks(title)


# endregion


# region Config
@router.get("/api/config", response_model=GlobalConfigResponseModel)
def get_config():
    """Retrieve server-side config required for the UI."""
    return GlobalConfigResponseModel(
        auth_type=global_config.auth_type,
        quick_access_hide=global_config.quick_access_hide,
        quick_access_title=global_config.quick_access_title,
        quick_access_term=global_config.quick_access_term,
        quick_access_sort=global_config.quick_access_sort,
        quick_access_limit=global_config.quick_access_limit,
    )


# endregion


# region Git Sync

class GitConfigModel(BaseModel):
    remote_url: str = ""
    auth_type: str = "token"
    token: str = ""


def _get_storage_path() -> str:
    return get_env("FLATNOTES_PATH", default="/data")


def _get_git_config_path() -> str:
    return os.path.join(_get_storage_path(), ".flatnotes", "git-config.json")


def _load_git_config() -> dict:
    config_path = _get_git_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"remote_url": "", "auth_type": "token", "token": ""}


def _save_git_config(config: dict) -> None:
    config_path = _get_git_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f)


@router.get("/api/git-config", dependencies=auth_deps)
def get_git_config():
    """Get the current git sync configuration."""
    config = _load_git_config()
    return {"remote_url": config.get("remote_url", ""), "auth_type": config.get("auth_type", "token")}


@router.post("/api/git-config", dependencies=auth_deps)
def set_git_config(data: GitConfigModel):
    """Set the git sync configuration."""
    config = _load_git_config()
    config["remote_url"] = data.remote_url
    config["auth_type"] = data.auth_type
    if data.token:
        config["token"] = data.token
    _save_git_config(config)
    return {"status": "ok"}


@router.post("/api/git-verify", dependencies=auth_deps)
def verify_git_sync():
    """Verify git sync by creating a test file, committing, and pushing."""
    config = _load_git_config()
    remote_url = config.get("remote_url", "")
    auth_type = config.get("auth_type", "token")
    token = config.get("token", "")

    if not remote_url:
        raise HTTPException(status_code=400, detail="No remote URL configured")

    storage_path = _get_storage_path()
    repo_root = _find_git_root(storage_path)

    if not repo_root:
        raise HTTPException(status_code=400, detail="Not a git repository")

    try:
        # Set remote URL with auth
        if auth_type == "token" and token:
            authed_url = remote_url.replace("https://", f"https://{token}@")
            subprocess.run(
                ["git", "remote", "set-url", "origin", authed_url],
                cwd=repo_root, capture_output=True, timeout=10,
            )
        else:
            subprocess.run(
                ["git", "remote", "set-url", "origin", remote_url],
                cwd=repo_root, capture_output=True, timeout=10,
            )

        # Create a test file
        test_file = os.path.join(storage_path, ".slingshot-sync-test.md")
        with open(test_file, "w") as f:
            f.write(f"# Slingshot Sync Test\n\nVerified at: {datetime.now()}\n")

        subprocess.run(["git", "add", "-A"], cwd=repo_root, capture_output=True, timeout=10)
        result = subprocess.run(
            ["git", "commit", "-m", "slingshot: verify sync", "--allow-empty"],
            cwd=repo_root, capture_output=True, timeout=10, text=True,
        )
        push = subprocess.run(
            ["git", "push", "origin", "HEAD"],
            cwd=repo_root, capture_output=True, timeout=30, text=True,
        )

        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)
            subprocess.run(["git", "add", "-A"], cwd=repo_root, capture_output=True, timeout=5)
            subprocess.run(
                ["git", "commit", "-m", "slingshot: cleanup sync test", "--allow-empty"],
                cwd=repo_root, capture_output=True, timeout=5,
            )
            subprocess.run(["git", "push", "origin", "HEAD"], cwd=repo_root, capture_output=True, timeout=30)

        # Reset remote URL to clean version
        subprocess.run(
            ["git", "remote", "set-url", "origin", remote_url],
            cwd=repo_root, capture_output=True, timeout=5,
        )

        if push.returncode == 0:
            return {"status": "success", "message": "Sync verified successfully!"}
        else:
            error_msg = push.stderr or "Unknown error"
            return {"status": "error", "message": error_msg}

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Operation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _find_git_root(path: str) -> Optional[str]:
    """Find the git repository root by searching upwards."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path, capture_output=True, timeout=5, text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


# endregion


# region Attachments
# Get Attachment
@router.get(
    "/api/attachments/{filename}",
    dependencies=auth_deps,
)
# Include a secondary route used to create relative URLs that can be used
# outside the context of flatnotes (e.g. "/attachments/image.jpg").
@router.get(
    "/attachments/{filename}",
    dependencies=auth_deps,
    include_in_schema=False,
)
def get_attachment(filename: str):
    """Download an attachment."""
    try:
        return attachment_storage.get(filename)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=api_messages.invalid_attachment_filename,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=api_messages.attachment_not_found
        )


if global_config.auth_type != AuthType.READ_ONLY:

    # Create Attachment
    @router.post(
        "/api/attachments",
        dependencies=auth_deps,
        response_model=AttachmentCreateResponse,
    )
    def post_attachment(file: UploadFile):
        """Upload an attachment."""
        try:
            return attachment_storage.create(file)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_attachment_filename,
            )
        except FileExistsError:
            raise HTTPException(409, api_messages.attachment_exists)


# endregion


# region Healthcheck
@router.get("/health")
def healthcheck() -> str:
    """A lightweight endpoint that simply returns 'OK' to indicate the server
    is running."""
    return "OK"


# endregion

app.include_router(router, prefix=global_config.path_prefix)
app.mount(
    global_config.path_prefix,
    StaticFiles(directory="client/dist"),
    name="dist",
)
