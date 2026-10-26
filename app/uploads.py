"""File upload handling: content sniffing, streamed size limits, safe names and deletes."""
import os
import re
import secrets
import unicodedata
from pathlib import Path

from fastapi import UploadFile

from app.errors import ApiError

CHUNK = 64 * 1024
MB = 1024 * 1024

# kind -> (canonical extension, accepted extensions)
KINDS = {
    "jpeg": (".jpg", {".jpg", ".jpeg"}),
    "png": (".png", {".png"}),
    "webp": (".webp", {".webp"}),
    "pdf": (".pdf", {".pdf"}),
}
LABELS = {"jpeg": "JPG", "png": "PNG", "webp": "WEBP", "pdf": "PDF"}


def sniff(head: bytes) -> str | None:
    """Identify a file from its first bytes. Never trusts the filename or Content-Type."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head.startswith(b"%PDF-"):
        return "pdf"
    return None


def slugify(text: str, max_length: int = 50) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:max_length].rstrip("-") or "file"


def is_present(upload: UploadFile | None) -> bool:
    """Browsers send an empty part with no filename when a file input is left empty."""
    return upload is not None and bool(upload.filename)


def save_upload(upload: UploadFile, dest_dir: Path, allowed: set[str], max_bytes: int,
                name_stem: str, field: str = "file") -> str:
    """Stream an upload to dest_dir, validating type by content and size while reading.

    Returns the stored filename. Raises ApiError (413/415/422) and leaves nothing behind on failure.
    """
    allowed_labels = ", ".join(LABELS[k] for k in sorted(allowed))
    original = upload.filename or ""
    ext = os.path.splitext(original)[1].lower()
    accepted_exts = set().union(*(KINDS[k][1] for k in allowed))
    if ext not in accepted_exts:
        raise ApiError(415, f"{original or 'File'}: only {allowed_labels} files are allowed.",
                       fields={field: f"Only {allowed_labels} files are allowed."})

    dest_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_dir / f".upload-{secrets.token_hex(8)}.part"
    size = 0
    kind = None
    try:
        upload.file.seek(0)
        with open(tmp_path, "wb") as out:
            while chunk := upload.file.read(CHUNK):
                if kind is None:
                    kind = sniff(chunk[:16])
                    if kind not in allowed:
                        raise ApiError(415, f"{original}: the file content is not a valid {allowed_labels} file.",
                                       fields={field: f"File content is not a valid {allowed_labels} file."})
                    if ext not in KINDS[kind][1]:
                        raise ApiError(415, f"{original}: the file extension does not match its content.",
                                       fields={field: "File extension does not match its content."})
                size += len(chunk)
                if size > max_bytes:
                    limit = f"{max_bytes // MB} MB"
                    raise ApiError(413, f"{original}: file is larger than {limit}.",
                                   fields={field: f"Maximum file size is {limit}."})
                out.write(chunk)
        if size == 0:
            raise ApiError(422, f"{original}: file is empty.", fields={field: "File is empty."})

        filename = f"{name_stem}-{secrets.token_hex(3)}{KINDS[kind][0]}"
        final_path = dest_dir / filename
        while final_path.exists():  # astronomically unlikely, but never overwrite
            filename = f"{name_stem}-{secrets.token_hex(3)}{KINDS[kind][0]}"
            final_path = dest_dir / filename
        os.replace(tmp_path, final_path)
        return filename
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def resolve_inside(base_dir: Path, name: str) -> Path | None:
    """Return base_dir/name only if it stays inside base_dir (guards against path traversal)."""
    base = base_dir.resolve()
    target = (base / name).resolve()
    return target if target.parent == base else None


def delete_file(base_dir: Path, name: str) -> None:
    target = resolve_inside(base_dir, name)
    if target is not None:
        target.unlink(missing_ok=True)
