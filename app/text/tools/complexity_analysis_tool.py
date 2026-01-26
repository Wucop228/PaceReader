import json
from typing import Any

from app.text.perplexity_client import call_perplexity_api


async def analyze_text_complexity(text: str) -> dict[str, Any]:
    try:
        if not text or text.strip() == "":
            return {
                "success": False,
                "error": "Текст для анализа пуст",
                "recommended_level": "medium"
            }

        text_sample = text[:3000] if len(text) > 3000 else text
        prompt = _get_analysis_prompt(text_sample)

        messages = [
            {
                "role": "system",
                "content": "Ты эксперт по анализу текстов. Отвечай строго в формате JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        analysis_result = await call_perplexity_api(
            messages=messages,
            temperature=0.2
        )

        try:
            analysis = json.loads(analysis_result)
            return {
                "success": True,
                "recommended_level": analysis.get("level", "medium"),
                "reasoning": analysis.get("reasoning", ""),
                "text_stats": analysis.get("stats", {})
            }
        except json.JSONDecodeError:
            return _parse_text_response(analysis_result)

    except Exception as e:
        return {
            "success": False,
            "error": f"Ошибка анализа: {str(e)}",
            "recommended_level": "medium"
        }


def _get_analysis_prompt(text: str) -> str:
    word_count = len(text.split())

    return f"""Проанализируй текст и определи оптимальный уровень детализации для резюме.

Критерии оценки:
1. **Водность** (много повторов, общих фраз без конкретики):
   - Высокая водность → рекомендуй "tldr" или "short"

2. **Информативность** (конкретные факты, цифры, детали):
   - Высокая информативность → рекомендуй "detailed"

3. **Структурированность** (есть заголовки, разделы, списки):
   - Хорошая структура → рекомендуй "medium" или "detailed"

4. **Объем текста**:
   - < 500 слов → "short"
   - 500-2000 слов → "medium"
   - > 2000 слов → "detailed"

Текст содержит примерно {word_count} слов.

Верни СТРОГО JSON в формате:
{{
  "level": "tldr|short|medium|detailed",
  "reasoning": "краткое объяснение выбора (1-2 предложения)",
  "stats": {{
    "words": {word_count},
    "has_structure": true/false,
    "info_density": "low|medium|high"
  }}
}}

Текст для анализа:
{text}"""


def _parse_text_response(response: str) -> dict[str, Any]:
    response_lower = response.lower()

    if "tldr" in response_lower:
        level = "tldr"
    elif "short" in response_lower:
        level = "short"
    elif "detailed" in response_lower:
        level = "detailed"
    else:
        level = "medium"

    return {
        "success": True,
        "recommended_level": level,
        "reasoning": response,
        "text_stats": {}
    }


def get_tool_spec() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "analyze_text_complexity",
            "description": (
                "Анализирует текст и определяет оптимальный уровень детализации резюме. "
                "Оценивает водность, структурированность, информативность. "
                "Возвращает рекомендацию: tldr, short, medium или detailed. "
                "Используй ТОЛЬКО когда пользователь явно выбрал режим AUTO для уровня детализации."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Текст для анализа сложности"
                    }
                },
                "required": ["text"]
            }
        }
    }