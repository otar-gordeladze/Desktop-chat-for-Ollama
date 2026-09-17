"""Attachment import, classification, and content extraction."""
from __future__ import annotations

import mimetypes
import shutil
import uuid
from pathlib import Path

from pypdf import PdfReader

from app.models.entities import Attachment
from app.utils.paths import attachments_dir

TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".py", ".js", ".ts", ".tsx", ".jsx", ".json",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".csv", ".html", ".css", ".xml",
    ".sql", ".sh", ".c", ".cpp", ".h", ".hpp", ".java", ".rs", ".go",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


class FileService:
    """Copies selected files into managed storage and extracts safe text content."""

    def import_file(self, source: Path) -> Attachment:
        if not source.is_file():
            raise FileNotFoundError(source)
        ext = source.suffix.lower()
        mime_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        kind = "image" if ext in IMAGE_EXTENSIONS else "pdf" if ext == ".pdf" else "text" if ext in TEXT_EXTENSIONS else "file"
        target = attachments_dir() / f"{uuid.uuid4().hex}{ext}"
        shutil.copy2(source, target)
        return Attachment(
            id=None,
            message_id=None,
            original_name=source.name,
            stored_path=target,
            mime_type=mime_type,
            size_bytes=target.stat().st_size,
            kind=kind,  # type: ignore[arg-type]
        )

    def extract_text(self, attachment: Attachment, max_chars: int = 50000) -> str:
        """Return textual attachment content; unsupported binary files return an explanation."""
        try:
            if attachment.kind == "text":
                return attachment.stored_path.read_text(encoding="utf-8", errors="replace")[:max_chars]
            if attachment.kind == "pdf":
                reader = PdfReader(str(attachment.stored_path))
                chunks: list[str] = []
                used = 0
                for page in reader.pages:
                    text = page.extract_text() or ""
                    remaining = max_chars - used
                    if remaining <= 0:
                        break
                    chunks.append(text[:remaining])
                    used += len(chunks[-1])
                return "\n".join(chunks)
        except Exception as exc:  # Extraction failure should not crash the whole chat.
            return f"[Could not extract {attachment.original_name}: {exc}]"
        return f"[Attached binary file: {attachment.original_name}; no text extractor is configured for this file type.]"
