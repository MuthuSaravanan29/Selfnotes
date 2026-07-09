<p align="center">
  <h1 align="center">Slingshot</h1>
</p>

An Obsidian-like, self-hosted note-taking web app with markdown files, git auto-sync, and a modern UI.

> Forked from [flatnotes](https://github.com/dullage/flatnotes) with Obsidian-inspired features.

## Features

- **File Explorer sidebar** — tree view of all notes with search/filter
- **Split Pane editor** — edit markdown with live preview side by side
- **Command Palette** — Ctrl+P / Ctrl+K to search commands and notes
- **Backlinks Panel** — shows which notes link to the current note via `[[wikilinks]]`
- **Tags Panel** — collapsible tag list in sidebar, click to filter
- **Daily Notes** — one-click daily journal with template
- **Notes Sync** — built-in UI to configure git sync (token or SSH)
- **Auto git sync** — every note save auto-commits and pushes to your repository
- **Full-text search** — powerful search with tag filtering
- **Light/Dark themes** — toggleable theme
- **Authentication** — password / read-only / 2FA modes

## Getting Started

### Docker Run

```shell
docker run -d \
  -p 2908:2908 \
  -e "FLATNOTES_USERNAME=admin" \
  -e "FLATNOTES_PASSWORD=slingshot123" \
  -e "FLATNOTES_SECRET_KEY=$(openssl rand -base64 32)" \
  -v "$(pwd)/data:/data" \
  slingshot:latest
```

Open **http://localhost:2908** and log in with the credentials above.

### Docker Compose

```yaml
version: "3"

services:
  slingshot:
    container_name: slingshot
    image: slingshot:latest
    environment:
      FLATNOTES_AUTH_TYPE: "password"
      FLATNOTES_USERNAME: "admin"
      FLATNOTES_PASSWORD: "slingshot123"
      FLATNOTES_SECRET_KEY: "your-secret-key-here"
    volumes:
      - "./data:/data"
    ports:
      - "2908:2908"
    restart: unless-stopped
```

### Building from source

```shell
git clone https://github.com/MuthuSaravanan29/Selfnotes.git
cd Selfnotes
npm install
npm run build
pip install pipenv
pipenv install --deploy --ignore-pipfile --system
python -m uvicorn main:app --app-dir server --host 0.0.0.0 --port 2908
```

## Notes Sync

Slingshot can automatically sync all your notes to a Git repository.

1. Click the **Sync** button in the top bar (or Ctrl+P → "Notes Sync")
2. Enter your repository URL (e.g., `https://github.com/user/repo.git`)
3. Choose authentication:
   - **Token**: Enter your GitHub Personal Access Token (requires `repo` scope)
   - **SSH**: Follow the on-screen steps to add your SSH key to GitHub
4. Click **Verify & Save** — Slingshot will create a test note, commit, and push to verify the connection
5. Once verified, every note you create/edit/delete is **automatically committed and pushed** to your repository

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FLATNOTES_PORT` | `2908` | Server port |
| `FLATNOTES_AUTH_TYPE` | `password` | Auth mode: `none`, `read_only`, `password`, `totp` |
| `FLATNOTES_USERNAME` | `admin` | Login username |
| `FLATNOTES_PASSWORD` | `slingshot123` | Login password |
| `FLATNOTES_SECRET_KEY` | (required) | JWT signing key |
| `FLATNOTES_PATH` | `/data` | Notes storage directory |
| `PUID` / `PGID` | `1000` | File ownership |

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `/` | Search |
| `Ctrl+P` / `Ctrl+K` | Command Palette |
| `Ctrl+\` | Toggle Sidebar |
| `Ctrl+Alt+N` | New Note |
| `Ctrl+Alt+H` | Go to Home |
| `E` | Edit note (in view mode) |
| `Ctrl+Enter` | Save note |
| `Escape` | Cancel / Close |

## Tech Stack

- **Frontend:** Vue 3, Tailwind CSS, TOAST UI Editor
- **Backend:** Python / FastAPI
- **Search:** Whoosh (pure Python full-text search)
- **Storage:** Flat markdown files (no database)
- **Auth:** JWT with optional TOTP 2FA
