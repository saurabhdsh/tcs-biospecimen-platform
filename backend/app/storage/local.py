from pathlib import Path

from app.core.config import settings
from app.storage.base import FileStorage


class LocalFileStorage(FileStorage):
    """Local filesystem storage. Replace with S3/Azure Blob adapter later."""

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.upload_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, data: bytes) -> str:
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read(self, key: str) -> bytes:
        return self.path_for(key).read_bytes()

    def path_for(self, key: str) -> Path:
        return self.root / key

    def exists(self, key: str) -> bool:
        return self.path_for(key).exists()


storage = LocalFileStorage()
