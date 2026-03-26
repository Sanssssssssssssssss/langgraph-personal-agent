from __future__ import annotations

import hashlib
import mimetypes
import shutil
from pathlib import Path

from pypdf import PdfReader


class FileStorage:
    def __init__(self, upload_dir: str | Path) -> None:
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def store_file(self, source_path: str | Path) -> dict[str, str]:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(source)
        checksum = hashlib.sha256(source.read_bytes()).hexdigest()
        target = self.upload_dir / f"{checksum[:12]}_{source.name}"
        shutil.copy2(source, target)
        media_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        return {
            "stored_path": str(target),
            "checksum": checksum,
            "media_type": media_type,
            "source_name": source.name,
            "extension": source.suffix.lower(),
        }

    def extract_text(self, stored_path: str | Path) -> str:
        path = Path(stored_path)
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return path.read_text(encoding="utf-8")
        if suffix == ".pdf":
            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        raise ValueError(f"Unsupported file type: {suffix}")
