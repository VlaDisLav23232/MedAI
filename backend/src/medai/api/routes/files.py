"""File upload endpoints — images, audio, documents.

Accepts multipart file uploads, categorises by MIME type,
stores locally under ./storage/uploads/, and returns URLs
the frontend can pass to /cases/analyze.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile
from pydantic import BaseModel, Field

from medai.api.auth import get_current_user
from medai.config import get_settings
from medai.domain.entities import User

logger = structlog.get_logger()

router = APIRouter(prefix="/files", tags=["files"])

# ── MIME → category mapping ───────────────────────────────

IMAGE_MIMES = {
    "image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp",
    "image/tiff", "image/svg+xml", "application/dicom",
}
AUDIO_MIMES = {
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/aac",
    "audio/flac", "audio/webm", "audio/x-wav", "audio/x-m4a",
}
DOCUMENT_MIMES = {
    "application/pdf", "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# File extension fallbacks for when MIME is generic
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".tif", ".svg", ".dcm", ".dicom"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".webm", ".wma"}
DOCUMENT_EXTS = {".pdf", ".txt", ".doc", ".docx"}

ALL_ALLOWED_MIMES = IMAGE_MIMES | AUDIO_MIMES | DOCUMENT_MIMES
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


FileCategory = Literal["image", "audio", "document"]


def _detect_category(content_type: str | None, filename: str) -> FileCategory:
    """Detect file category from MIME type, falling back to extension."""
    ct = (content_type or "").lower()
    if ct in IMAGE_MIMES:
        return "image"
    if ct in AUDIO_MIMES:
        return "audio"
    if ct in DOCUMENT_MIMES:
        return "document"

    # Fallback to extension
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in DOCUMENT_EXTS:
        return "document"

    # Default — treat unknown as document
    return "document"


def _is_allowed(content_type: str | None, filename: str) -> bool:
    """Check if file is allowed by MIME or extension."""
    ct = (content_type or "").lower()
    if ct in ALL_ALLOWED_MIMES:
        return True
    ext = Path(filename).suffix.lower()
    return ext in (IMAGE_EXTS | AUDIO_EXTS | DOCUMENT_EXTS)


# ── Response schemas ──────────────────────────────────────

class UploadedFileInfo(BaseModel):
    """Info about a single uploaded file."""
    id: str
    original_name: str
    category: FileCategory
    content_type: str
    size: int
    url: str


class UploadResponse(BaseModel):
    """Response for file upload."""
    files: list[UploadedFileInfo]
    image_urls: list[str] = Field(default_factory=list)
    audio_urls: list[str] = Field(default_factory=list)
    document_urls: list[str] = Field(default_factory=list)


# ── Upload endpoint ───────────────────────────────────────

@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: list[UploadFile] = FastAPIFile(..., description="Files to upload (images, audio, documents)"),
    _current_user: User = Depends(get_current_user),
) -> UploadResponse:
    """Upload one or more files (images, audio, documents).

    Files are saved locally and URLs are returned, pre-sorted by
    category so the frontend can directly pass them to /cases/analyze.
    """
    settings = get_settings()
    upload_dir = settings.storage_local_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    results: list[UploadedFileInfo] = []
    image_urls: list[str] = []
    audio_urls: list[str] = []
    document_urls: list[str] = []

    for f in files:
        fname = f.filename or "unknown"

        # Validate file type
        if not _is_allowed(f.content_type, fname):
            raise HTTPException(
                status_code=415,
                detail=f"File type not allowed: {fname} ({f.content_type}). "
                       f"Allowed: images, audio, PDF/TXT/DOC/DOCX.",
            )

        # Read file content
        content = await f.read()

        # Validate size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {fname} ({len(content) / 1024 / 1024:.1f} MB). Max: {MAX_FILE_SIZE / 1024 / 1024:.0f} MB.",
            )

        # Detect category
        category = _detect_category(f.content_type, fname)

        # Generate unique filename
        file_id = uuid.uuid4().hex[:12]
        ext = Path(fname).suffix.lower() or ".bin"
        ts = datetime.utcnow().strftime("%Y%m%d")
        stored_name = f"{ts}_{file_id}{ext}"
        dest = upload_dir / stored_name

        # Write to disk
        dest.write_bytes(content)
        url = f"/storage/uploads/{stored_name}"

        logger.info(
            "file_uploaded",
            file_id=file_id,
            name=fname,
            category=category,
            size=len(content),
            content_type=f.content_type,
            path=str(dest),
        )

        info = UploadedFileInfo(
            id=file_id,
            original_name=fname,
            category=category,
            content_type=f.content_type or "application/octet-stream",
            size=len(content),
            url=url,
        )
        results.append(info)

        if category == "image":
            image_urls.append(url)
        elif category == "audio":
            audio_urls.append(url)
        else:
            document_urls.append(url)

    return UploadResponse(
        files=results,
        image_urls=image_urls,
        audio_urls=audio_urls,
        document_urls=document_urls,
    )
