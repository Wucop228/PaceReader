from typing import Any

from app.core.config import settings
from app.text.enums import SummaryLevel
from app.text.gigachat_client import gigachat_chat_with_tools
from app.text.tools import get_default_tools, execute_tool
from app.text.schemas import SummarizeRequest


def _build_system_prompt() -> str:
    return """Ты умный агент для суммаризации документов.

У тебя есть доступ к инструментам (tools):
- anonymize_data - обезличивает конфиденциальные данные (принимает file_path ИЛИ text)

Правила работы:
1. ВСЕГДА сначала вызывай anonymize_data для обработки данных
   - Если получил file_path - передай file_path
   - Если получил text - передай text
   - НИКОГДА не передавай оба параметра одновременно!
2. Работай только с обезличенным текстом
3. Не выдумывай факты - используй только информацию из документа
4. Создавай структурированные и понятные резюме
5. Отвечай на русском языке"""


def _build_user_prompt(request: SummarizeRequest) -> str:
    level_instructions = {
        SummaryLevel.TLDR: "ультракороткое резюме (2-3 предложения)",
        SummaryLevel.SHORT: "краткое резюме (1-2 абзаца)",
        SummaryLevel.MEDIUM: "среднее резюме (3-5 абзацев)",
        SummaryLevel.DETAILED: "подробное структурированное резюме со всеми важными деталями"
    }

    if request.file_path:
        source_info = f"Файл для обработки: {request.file_path}"
        anonymize_instruction = f'1. Вызови anonymize_data с параметром file_path="{request.file_path}"'
    else:
        source_info = "Текст для обработки передан напрямую"
        anonymize_instruction = '1. Вызови anonymize_data с параметром text="<переданный текст>"'

    if request.level == SummaryLevel.AUTO:
        return f"""{source_info}

ЗАДАЧА:
{anonymize_instruction}
2. Проанализируй полученный текст:
   - Оцени водность (много повторов и общих фраз?)
   - Оцени информативность (много конкретных фактов, цифр, деталей?)
   - Оцени объем (сколько слов примерно?)
3. САМ выбери оптимальный уровень детализации:
   - tldr: если текст водянистый или очень короткий (< 300 слов)
   - short: если текст небольшой (300-500 слов)
   - medium: если текст среднего размера (500-2000 слов) и информативный
   - detailed: если текст длинный (> 2000 слов) или очень насыщен фактами
4. Создай резюме выбранного уровня
5. В начале ответа укажи: "Выбран уровень: [уровень], потому что [краткое объяснение]"

Создай качественное резюме документа."""
    else:
        instruction = level_instructions[request.level]
        return f"""{source_info}

ЗАДАЧА:
{anonymize_instruction}
2. Создай {instruction} на основе полученного текста

Требования к резюме:
- Сохрани все ключевые идеи и важные факты
- Убери воду, повторы и несущественные детали
- Сделай текст структурированным и легко читаемым
- Используй русский язык

Создай качественное резюме документа."""


async def summarize_with_agent(request: SummarizeRequest) -> dict[str, Any]:
    source_type = "file" if request.file_path else "text"
    source_value = request.file_path if request.file_path else (
        f"{request.text[:50]}..." if len(request.text) > 50 else request.text
    )

    messages = [
        {
            "role": "system",
            "content": _build_system_prompt()
        },
        {
            "role": "user",
            "content": _build_user_prompt(request)
        }
    ]

    if request.text:
        messages[1]["content"] += f"\n\nТекст:\n{request.text}"

    tools = get_default_tools()

    result = await gigachat_chat_with_tools(
        messages=messages,
        tools_specs=tools,
        execute_tool_func=execute_tool,
        model=request.model,
        temperature=request.temperature,
        max_steps=request.max_steps
    )

    return {
        "summary": result["content"],
        "level": request.level.value,
        "steps": result["steps"],
        "metadata": {
            "agent": "smart_summarizer_agent",
            "model": request.model or settings.GIGACHAT_DEFAULT_MODEL,
            "temperature": request.temperature,
            "source_type": source_type,
            "source": source_value,
            "total_steps": len(result["steps"])
        }
    }