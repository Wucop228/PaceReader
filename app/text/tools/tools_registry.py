from typing import Any

from app.text.tools import anonymization_tool, complexity_analysis_tool


TOOL_FUNCTIONS = {
    "anonymize_data": anonymization_tool.anonymize_data,
    "analyze_text_complexity": complexity_analysis_tool.analyze_text_complexity,
}


def get_default_tools() -> list[dict[str, Any]]:
    return [
        anonymization_tool.get_tool_spec(),
        # complexity_analysis_tool.get_tool_spec(),
    ]


async def execute_tool(function_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    func = TOOL_FUNCTIONS.get(function_name)

    if not func:
        return {
            "success": False,
            "error": f"Функция '{function_name}' не найдена в tools"
        }

    try:
        result = await func(**arguments)
        return result
    except TypeError as e:
        return {
            "success": False,
            "error": f"Неверные аргументы для функции '{function_name}': {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Ошибка выполнения функции '{function_name}': {str(e)}"
        }