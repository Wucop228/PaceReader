import uuid
from pathlib import Path

from fastapi import HTTPException, status, UploadFile

from app.core.config import settings


def validate_upload_file(file: UploadFile) -> None:
    filename = file.filename or ""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Файл не найден: {filename}",
        )
    if not settings.is_file_extension_allowed(filename):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Недопустимое расширение файла: {Path(filename).suffix}",
        )


async def save_upload_file(file: UploadFile) -> str:
    validate_upload_file(file)

    raw = await file.read()
    if not settings.validate_file_size(len(raw)):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Файл слишком большой. Максимум {settings.MAX_FILE_SIZE_MB} MB",
        )

    ext = Path(file.filename).suffix.lower()
    new_name = f"{uuid.uuid4()}{ext}"
    dest_path = settings.upload_path / new_name

    with open(dest_path, "wb") as f:
        f.write(raw)

    return str(dest_path)