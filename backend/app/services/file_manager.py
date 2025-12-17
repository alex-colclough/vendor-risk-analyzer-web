"""Secure file management service."""

import hashlib
import os
import secrets
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiofiles
import magic
from fastapi import UploadFile

from app.config import settings
from app.models.responses import UploadedFile


class FileValidationError(Exception):
    """Raised when file validation fails."""

    pass


class FileManager:
    """Secure file manager for handling uploads."""

    # Magic numbers for file type validation
    MAGIC_SIGNATURES = {
        b"%PDF": "application/pdf",
        b"PK\x03\x04": "application/zip",  # DOCX, XLSX are ZIP-based
        b"\xd0\xcf\x11\xe0": "application/vnd.ms-excel",  # XLS (OLE)
    }

    def __init__(self, upload_dir: Optional[Path] = None):
        self.upload_dir = upload_dir or settings.upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self._mime = magic.Magic(mime=True)

    def _get_session_dir(self, session_id: str) -> Path:
        """Get isolated directory for session."""
        # Sanitize session_id to prevent path traversal
        safe_session_id = "".join(
            c for c in session_id if c.isalnum() or c == "-"
        )
        return self.upload_dir / safe_session_id

    def _generate_file_id(self) -> str:
        """Generate cryptographically secure file ID."""
        return secrets.token_urlsafe(16)

    def _validate_extension(self, filename: str) -> str:
        """Validate and return file extension."""
        ext = Path(filename).suffix.lower()
        if ext not in settings.allowed_extensions:
            raise FileValidationError(
                f"File extension '{ext}' not allowed. "
                f"Allowed: {', '.join(settings.allowed_extensions)}"
            )
        return ext

    def _validate_mime_type(self, file_path: Path, expected_ext: str) -> str:
        """Validate file MIME type using magic numbers."""
        mime_type = self._mime.from_file(str(file_path))

        # Handle ZIP-based formats (DOCX, XLSX)
        if mime_type == "application/zip":
            if expected_ext == ".docx":
                mime_type = (
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                )
            elif expected_ext in (".xlsx", ".xls"):
                mime_type = (
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )

        # Special handling for text files
        if mime_type.startswith("text/") and expected_ext in (".txt", ".md", ".csv"):
            if expected_ext == ".csv":
                mime_type = "text/csv"
            elif expected_ext == ".md":
                mime_type = "text/markdown"
            else:
                mime_type = "text/plain"

        if mime_type not in settings.allowed_mime_types:
            raise FileValidationError(
                f"File type '{mime_type}' not allowed for extension '{expected_ext}'"
            )

        return mime_type

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and injection."""
        # Get just the filename part
        name = Path(filename).name
        # Remove any null bytes
        name = name.replace("\x00", "")
        # Replace potentially dangerous characters
        safe_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_ "
        )
        name = "".join(c if c in safe_chars else "_" for c in name)
        # Limit length
        if len(name) > 255:
            ext = Path(name).suffix
            name = name[: 255 - len(ext)] + ext
        return name

    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    async def save_upload(
        self, session_id: str, file: UploadFile
    ) -> UploadedFile:
        """
        Securely save an uploaded file.

        Args:
            session_id: Session identifier
            file: Uploaded file from FastAPI

        Returns:
            UploadedFile model with file metadata

        Raises:
            FileValidationError: If validation fails
        """
        # Validate extension
        extension = self._validate_extension(file.filename or "unknown")

        # Create session directory
        session_dir = self._get_session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        # Generate secure file ID and path
        file_id = self._generate_file_id()
        safe_filename = f"{file_id}{extension}"
        file_path = session_dir / safe_filename

        # Check total session size before saving
        current_size = sum(
            f.stat().st_size for f in session_dir.iterdir() if f.is_file()
        )

        # Read and save file with size check
        total_size = 0
        try:
            async with aiofiles.open(file_path, "wb") as out_file:
                while chunk := await file.read(8192):
                    total_size += len(chunk)
                    if total_size > settings.max_file_size_bytes:
                        raise FileValidationError(
                            f"File exceeds maximum size of {settings.max_file_size_mb}MB"
                        )
                    if current_size + total_size > settings.max_total_size_bytes:
                        raise FileValidationError(
                            f"Session total exceeds {settings.max_total_size_mb}MB"
                        )
                    await out_file.write(chunk)
        except FileValidationError:
            # Clean up partial file
            if file_path.exists():
                file_path.unlink()
            raise

        # Validate MIME type
        try:
            mime_type = self._validate_mime_type(file_path, extension)
        except FileValidationError:
            file_path.unlink()
            raise

        # Store original filename mapping securely
        original_name = self._sanitize_filename(file.filename or "unknown")
        meta_path = session_dir / f"{file_id}.meta"
        async with aiofiles.open(meta_path, "w") as meta_file:
            await meta_file.write(f"{original_name}\n{mime_type}")

        return UploadedFile(
            id=file_id,
            original_name=original_name,
            size_bytes=total_size,
            mime_type=mime_type,
            uploaded_at=datetime.utcnow(),
        )

    async def get_session_files(self, session_id: str) -> list[UploadedFile]:
        """Get all files for a session."""
        session_dir = self._get_session_dir(session_id)
        if not session_dir.exists():
            return []

        files = []
        for meta_file in session_dir.glob("*.meta"):
            file_id = meta_file.stem
            async with aiofiles.open(meta_file, "r") as f:
                content = await f.read()
                lines = content.strip().split("\n")
                original_name = lines[0]
                mime_type = lines[1] if len(lines) > 1 else "application/octet-stream"

            # Find corresponding data file
            data_files = list(session_dir.glob(f"{file_id}.*"))
            data_files = [f for f in data_files if not f.suffix == ".meta"]

            if data_files:
                data_file = data_files[0]
                files.append(
                    UploadedFile(
                        id=file_id,
                        original_name=original_name,
                        size_bytes=data_file.stat().st_size,
                        mime_type=mime_type,
                        uploaded_at=datetime.fromtimestamp(
                            data_file.stat().st_mtime
                        ),
                    )
                )

        return files

    async def get_file_path(self, session_id: str, file_id: str) -> Optional[Path]:
        """Get the actual file path for a file ID."""
        session_dir = self._get_session_dir(session_id)
        if not session_dir.exists():
            return None

        # Find file with matching ID
        for file_path in session_dir.iterdir():
            if file_path.stem == file_id and file_path.suffix != ".meta":
                return file_path

        return None

    async def delete_file(self, session_id: str, file_id: str) -> bool:
        """Delete a specific file."""
        session_dir = self._get_session_dir(session_id)
        if not session_dir.exists():
            return False

        deleted = False
        for file_path in session_dir.glob(f"{file_id}*"):
            file_path.unlink()
            deleted = True

        return deleted

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up all files for a session."""
        session_dir = self._get_session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)

    async def cleanup_expired_sessions(
        self, max_age_hours: int = 24
    ) -> int:
        """Clean up sessions older than max_age_hours."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned = 0

        for session_dir in self.upload_dir.iterdir():
            if not session_dir.is_dir():
                continue

            # Check directory modification time
            mtime = datetime.fromtimestamp(session_dir.stat().st_mtime)
            if mtime < cutoff:
                shutil.rmtree(session_dir)
                cleaned += 1

        return cleaned


# Global file manager instance
file_manager = FileManager()
