from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.text.perplexity_client import call_perplexity_api


async def anonymize_data(
        file_path: Optional[str] = None,
        text: Optional[str] = None
) -> dict[str, Any]:
    try:
        if file_path:
            result = await _anonymize_from_file(file_path)
            if result["success"]:
                result["source"] = "file"
            return result
        else:
            result = await _anonymize_from_text(text)
            if result["success"]:
                result["source"] = "text"
            return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Ошибка при анонимизации: {str(e)}"
        }


async def _anonymize_from_file(file_path: str) -> dict[str, Any]:
    path = Path(file_path)

    if not path.exists():
        return {
            "success": False,
            "error": f"Файл не найден: {file_path}"
        }

    if not settings.is_file_extension_allowed(str(path)):
        allowed = ", ".join(settings.ALLOWED_FILE_EXTENSIONS)
        return {
            "success": False,
            "error": f"Неподдерживаемый формат {path.suffix}. Разрешены: {allowed}"
        }

    file_size = path.stat().st_size
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        return {
            "success": False,
            "error": f"Файл слишком большой. Максимум: {settings.MAX_FILE_SIZE_MB}MB"
        }

    try:
        text_content = _extract_text_from_file(path)
    except Exception as e:
        return {
            "success": False,
            "error": f"Ошибка извлечения текста: {str(e)}"
        }

    result = await _anonymize_from_text(text_content)
    if result["success"]:
        result["original_file"] = str(path)

    return result


def _extract_text_from_file(path: Path) -> str:
    ext = path.suffix.lower()

    if ext == ".txt":
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="cp1251")
            except UnicodeDecodeError:
                raise Exception("Не удалось прочитать .txt как UTF-8 или CP1251")

    if ext == ".pdf":
        from pypdf import PdfReader
        try:
            reader = PdfReader(str(path))
            parts = []
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                    if text.strip():
                        parts.append(text)
                except Exception:
                    continue

            text = "\n".join(parts).strip()
        except Exception as e:
            raise Exception(f"Не удалось извлечь текст из PDF: {str(e)}")

        if not text:
            raise Exception("В PDF не найден текст (возможно, это скан и нужен OCR)")

        return text

    if ext == ".pptx":
        raise Exception("PPTX пока не поддерживается")

    raise Exception(f"Неподдерживаемый формат: {ext}")


async def _anonymize_from_text(text: str) -> dict[str, Any]:
    if not text or text.strip() == "":
        return {
            "success": False,
            "error": "Текст для анонимизации пуст"
        }

    messages = [
        {
            "role": "system",
            "content": "Ты помощник по обработке конфиденциальных документов. Строго следуй инструкциям."
        },
        {
            "role": "user",
            "content": f"""Замени все конфиденциальные данные на placeholder-ы:

- ФИО, имена людей → [ИМЯ]
- Номера телефонов → [ТЕЛЕФОН]
- Email адреса → [EMAIL]
- Физические адреса → [АДРЕС]
- Номера документов (паспорт, ИНН, СНИЛС) → [ДОКУМЕНТ]
- Номера счетов, карт → [СЧЕТ]

Верни ТОЛЬКО обработанный текст без пояснений.

Текст для обработки:
{text}"""
        }
    ]

    anonymized_text = await call_perplexity_api(
        messages=messages,
        temperature=0.1
    )

    return {
        "success": True,
        "anonymized_text": anonymized_text
    }


def get_tool_spec() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "anonymize_data",
            "description": (
                "Извлекает текст из файла или обрабатывает готовый текст и обезличивает конфиденциальные данные. "
                "Заменяет ФИО, телефоны, email, адреса, номера документов на placeholder-ы. "
                "Используй для обработки файлов (PDF/TXT/PPTX) или текста перед созданием резюме. "
                "Передай ЛИБО file_path ЛИБО text, но не оба одновременно."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Путь к файлу для обработки (PDF/TXT/PPTX). Используй если нужно обработать файл."
                    },
                    "text": {
                        "type": "string",
                        "description": "Готовый текст для обработки. Используй если текст уже есть (не файл)."
                    }
                },
                "required": []
            }
        }
    }