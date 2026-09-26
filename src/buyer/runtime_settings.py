import json
import os
import tempfile
import threading
from pathlib import Path


_settings_lock = threading.RLock()


def _settings_path():
    configured_path = os.getenv("IMMOWBOT_RUNTIME_SETTINGS_PATH")
    if configured_path:
        return Path(configured_path)
    return Path(__file__).resolve().parents[2] / "data" / "runtime-settings.json"


def read_runtime_settings():
    path = _settings_path()
    with _settings_lock:
        if path.is_symlink():
            raise ValueError("runtime settings file cannot be a symlink")
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as stream:
            settings = json.load(stream)
        if not isinstance(settings, dict):
            raise ValueError("runtime settings must be a JSON object")
        return settings


def write_runtime_settings(settings):
    if not isinstance(settings, dict):
        raise ValueError("runtime settings must be a JSON object")
    path = _settings_path()
    with _settings_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            raise ValueError("runtime settings file cannot be a symlink")
        descriptor, temporary_path = tempfile.mkstemp(prefix=".runtime-settings-", dir=path.parent)
        try:
            if os.name != "nt":
                os.chmod(temporary_path, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(settings, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, path)
            if os.name != "nt":
                os.chmod(path, 0o600)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
            raise
