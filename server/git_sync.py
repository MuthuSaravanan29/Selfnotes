import json
import os

from logger import logger


def load_git_config(storage_path: str) -> dict:
    config_path = os.path.join(storage_path, ".flatnotes", "git-config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load git config: {e}")
    return {}


def save_git_config(storage_path: str, config: dict) -> None:
    config_path = os.path.join(storage_path, ".flatnotes", "git-config.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f)


def save_ssh_key(storage_path: str, key_content: str) -> str:
    key_path = os.path.join(storage_path, ".flatnotes", "git-ssh-key")
    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    with open(key_path, "w") as f:
        f.write(key_content.strip())
        if not key_content.strip().endswith("\n"):
            f.write("\n")
    os.chmod(key_path, 0o600)
    return key_path


def get_git_ssh_env(storage_path: str) -> dict:
    config = load_git_config(storage_path)
    env = os.environ.copy()
    if config.get("auth_type") == "ssh":
        key_path = os.path.join(storage_path, ".flatnotes", "git-ssh-key")
        if os.path.exists(key_path):
            env["GIT_SSH_COMMAND"] = (
                f"ssh -i {key_path} -o StrictHostKeyChecking=no -o IdentitiesOnly=yes"
            )
    return env


def find_git_root(path: str) -> str | None:
    import subprocess

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
