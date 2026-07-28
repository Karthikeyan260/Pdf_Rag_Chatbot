import os
import uuid

from app.core.config import get_settings

settings = get_settings()


def save_upload(data: bytes, owner_id: str, original_filename: str) -> str:
    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(original_filename)}"
    directory = os.path.join(settings.storage_root, owner_id)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, safe_name)
    with open(path, "wb") as f:
        f.write(data)
    return path


def image_storage_dir(owner_id: str, document_id: str) -> str:
    directory = os.path.join(settings.storage_root, owner_id, "images", document_id)
    os.makedirs(directory, exist_ok=True)
    return directory


def read_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()
