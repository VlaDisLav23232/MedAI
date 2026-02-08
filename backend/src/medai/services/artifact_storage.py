"""Local artifact storage — saves heatmaps and other binary data to disk.

Converts base64 data URIs into local files, returning file paths
that the API can serve. Avoids bloating JSON responses with megabytes
of base64 data.
"""

from __future__ import annotations

import base64
import re
import uuid
from pathlib import Path

import structlog

logger = structlog.get_logger()

# Matches data:image/<type>;base64,<data>
_DATA_URI_RE = re.compile(r"^data:image/(\w+);base64,(.+)$", re.DOTALL)


class ArtifactStorage:
    """Saves binary artifacts (heatmaps, images) to local disk."""

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path
        self._base_path.mkdir(parents=True, exist_ok=True)

    def save_data_uri(
        self,
        data_uri: str,
        *,
        prefix: str = "heatmap",
        report_id: str = "",
    ) -> str | None:
        """Save a base64 data URI to disk. Returns the relative file path, or None on failure."""
        match = _DATA_URI_RE.match(data_uri)
        if not match:
            return None

        ext = match.group(1)  # png, jpeg, etc.
        b64_data = match.group(2)

        try:
            raw_bytes = base64.b64decode(b64_data)
        except Exception as e:
            logger.warning("artifact_decode_failed", error=str(e))
            return None

        # Build path: storage/<report_id>/<prefix>_<uuid>.<ext>
        subdir = self._base_path / (report_id or "misc")
        subdir.mkdir(parents=True, exist_ok=True)
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = subdir / filename

        filepath.write_bytes(raw_bytes)
        logger.debug("artifact_saved", path=str(filepath), size=len(raw_bytes))

        # Return relative path from storage root
        return str(filepath.relative_to(self._base_path))

    def save_json_artifact(
        self,
        data: dict | list,
        *,
        filename: str = "results.json",
        report_id: str = "",
    ) -> str:
        """Save a JSON artifact to disk. Returns the relative file path."""
        import json

        subdir = self._base_path / (report_id or "misc")
        subdir.mkdir(parents=True, exist_ok=True)
        filepath = subdir / filename

        filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.debug("json_artifact_saved", path=str(filepath))
        return str(filepath.relative_to(self._base_path))
