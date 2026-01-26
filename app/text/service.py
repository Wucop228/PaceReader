import asyncio

from app.text.schemas import SpeedReadInfo


def calculate_reading_info(summary_id: str, text: str, words_per_minute: int) -> SpeedReadInfo:
    words = text.split()
    word_count = len(words)
    estimated_duration_seconds = int((word_count / words_per_minute) * 60)

    return SpeedReadInfo(
        summary_id=summary_id,
        word_count=word_count,
        estimated_duration_seconds=estimated_duration_seconds,
        words_per_minute=words_per_minute,
    )


async def generate_speed_reading_stream(
        text: str,
        words_per_minute: int = 100
):
    if not text or not text.strip():
        return

    words = text.split()
    if not words:
        return

    delay = 60.0 / words_per_minute

    for word in words:
        yield f"data: {word}\n\n"
        await asyncio.sleep(delay)