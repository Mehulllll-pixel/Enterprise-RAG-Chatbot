import os
from typing import BinaryIO
from fastapi import UploadFile
from app.core.config import settings
from app.core.exceptions import ValidationException
from app.utils.logger import logger

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/octet-stream"  # Sometimes markdown/txt files upload as this
}

# Magic numbers signatures
MAGIC_SIGNATURES = {
    "pdf": b"%PDF",
    "docx": b"PK\x03\x04" # Zip signature
}

def validate_uploaded_file(file: UploadFile) -> None:
    """Validate file extension, MIME type, size, and header signatures to block malicious uploads."""
    filename = file.filename
    if not filename:
        raise ValidationException("Upload request is missing a valid filename.")

    _, ext = os.path.splitext(filename.lower())
    
    # 1. Validate Extension
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationException(
            f"File extension '{ext}' is not supported. Supported extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 2. Validate MIME Type
    if file.content_type not in ALLOWED_MIME_TYPES:
        # Note: some OS/browsers send empty or generic mime types, so we still check extension/header
        logger.warning(f"File uploaded with non-standard MIME type: {file.content_type} for {filename}")

    # 3. Validate File Size
    # Read file size without consuming memory completely by copying streams
    file.file.seek(0, os.SEEK_END)
    size_bytes = file.file.tell()
    file.file.seek(0)  # Reset pointer to start

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValidationException(
            f"File size ({size_bytes / 1024 / 1024:.2f} MB) exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB."
        )
        
    if size_bytes == 0:
        raise ValidationException("Uploaded file is empty (0 bytes).")

    # 4. Check Magic Byte Headers
    header_bytes = file.file.read(4)
    file.file.seek(0) # Reset pointer

    if ext == ".pdf":
        if not header_bytes.startswith(MAGIC_SIGNATURES["pdf"]):
            raise ValidationException("Invalid PDF file structure. File content signature does not match PDF standards.")
    elif ext == ".docx":
        if not header_bytes.startswith(MAGIC_SIGNATURES["docx"]):
            raise ValidationException("Invalid DOCX file structure. File content signature does not match Word standards.")
    
    logger.info(f"File validation passed for: {filename} ({size_bytes} bytes, type: {file.content_type})")
