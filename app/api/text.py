from pathlib import Path
from typing import Optional

from fastapi import APIRouter, status, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.core.config import settings
from app.core.database import get_db
from app.auth.dependencies import get_current_user_id

from app.text.enums import SourceType, SummaryStatus, SummaryLevel
from app.text.dao import DocumentDAO, SummaryDAO
from app.text.schemas import SummarizeRequest, SummaryResponse, SpeedReadInfo
from app.text.agents.smart_summarizer_agent import summarize_with_agent
from app.text.utils import save_upload_file
from app.text.service import generate_speed_reading_stream, calculate_reading_info

router = APIRouter(prefix="/text", tags=["text"])


@router.post("/summaries", status_code=status.HTTP_201_CREATED, response_model=SummaryResponse)
async def create_summary(
        user_id: str = Depends(get_current_user_id),
        session: AsyncSession = Depends(get_db),
        level: SummaryLevel = Form(SummaryLevel.MEDIUM),
        text: Optional[str] = Form(None),
        file: Optional[UploadFile] = File(None),
        model: Optional[str] = Form(None),
        temperature: float = Form(0.2),
        max_steps: int = Form(8),
):
    document_dao = DocumentDAO(session)
    summary_dao = SummaryDAO(session)

    file_path: Optional[str] = None
    original_text: Optional[str] = None

    if file is not None:
        file_path = await save_upload_file(file)
        source_type = SourceType.FILE
        original_text = f"[FILE: {Path(file_path).name}]"
    else:
        if text and len(text) > settings.MAX_TEXT_CHARS:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Текст слишком большой. Максимум {settings.MAX_TEXT_CHARS} символов",
            )
        original_text = text
        source_type = SourceType.TEXT

    document = await document_dao.add(
        source_type=source_type,
        original_text=original_text,
        file_path=file_path,
    )

    summary = await summary_dao.add(
        document_id=str(document.id),
        level=level,
        status=SummaryStatus.PROCESSING,
        summary_text=None,
        model=model or settings.GIGACHAT_DEFAULT_MODEL,
        error=None,
    )

    try:
        request = SummarizeRequest(
            file_path=file_path,
            text=text,
            level=level,
            model=model,
            temperature=temperature,
            max_steps=max_steps
        )

        result = await summarize_with_agent(request)

        await summary_dao.update(
            id=str(summary.id),
            status=SummaryStatus.DONE,
            summary_text=result["summary"],
            model=result["metadata"]["model"],
            error=None,
        )

    except ValidationError as e:
        await summary_dao.update(
            id=str(summary.id),
            status=SummaryStatus.ERROR,
            error="Ошибка валидации входных данных",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    except HTTPException:
        await summary_dao.update(
            id=str(summary.id),
            status=SummaryStatus.ERROR,
            error="Ошибка валидации входных данных",
        )
        raise

    except Exception as e:
        msg = str(e)

        await summary_dao.update(
            id=str(summary.id),
            status=SummaryStatus.ERROR,
            error=msg,
        )

        if "временно ограничены" in msg or "blacklist" in msg or "Запрос заблокирован" in msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Запрос заблокирован GigaChat"
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при суммаризации: {msg}"
        )

    updated = await summary_dao.find_one_or_none(id=str(summary.id))
    return updated


@router.get("/summaries/{summary_id}", status_code=status.HTTP_200_OK, response_model=SummaryResponse)
async def get_summary(
        summary_id: str,
        user_id: str = Depends(get_current_user_id),
        session: AsyncSession = Depends(get_db),
):
    dao = SummaryDAO(session)
    summary = await dao.find_one_or_none(id=summary_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary не найден"
        )

    return summary


@router.get(
    "/summaries/{summary_id}/speed-read-info",
    status_code=status.HTTP_200_OK,
    response_model=SpeedReadInfo
)
async def get_speed_read_info(
        summary_id: str,
        words_per_minute: int = Query(100, ge=50, le=1000),
        user_id: str = Depends(get_current_user_id),
        session: AsyncSession = Depends(get_db),
):
    dao = SummaryDAO(session)
    summary = await dao.find_one_or_none(id=summary_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary не найден"
        )

    if summary.status != SummaryStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Summary имеет статус {summary.status.value}, требуется {SummaryStatus.DONE.value}"
        )

    if not summary.summary_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Summary не содержит текста"
        )

    return calculate_reading_info(summary_id, summary.summary_text, words_per_minute)


@router.get("/summaries/{summary_id}/speed-read")
async def speed_read_summary(
        summary_id: str,
        words_per_minute: int = Query(100, ge=50, le=1000, description="Скорость чтения (слов в минуту)"),
        user_id: str = Depends(get_current_user_id),
        session: AsyncSession = Depends(get_db),
):
    dao = SummaryDAO(session)
    summary = await dao.find_one_or_none(id=summary_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary не найден"
        )

    if summary.status != SummaryStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Summary имеет статус {summary.status.value}"
        )

    if not summary.summary_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Summary не содержит текста"
        )

    return StreamingResponse(
        generate_speed_reading_stream(summary.summary_text, words_per_minute),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )