import json
from typing import Any, Optional

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole, Function, FunctionParameters, FunctionCall

from app.core.config import settings


def get_gigachat_client(
        model: Optional[str] = None,
) -> GigaChat:
    return GigaChat(
        credentials=settings.GIGACHAT_AUTH_KEY,
        model=model or settings.GIGACHAT_DEFAULT_MODEL,
        scope=settings.GIGACHAT_SCOPE,
        verify_ssl_certs=settings.GIGACHAT_VERIFY_SSL,
        timeout=settings.GIGACHAT_TIMEOUT,
    )


async def gigachat_chat_with_tools(
        *,
        messages: list[dict[str, Any]],
        tools_specs: list[dict[str, Any]],
        execute_tool_func: Any,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_steps: int = 8
) -> dict[str, Any]:
    client = get_gigachat_client(model=model)

    gigachat_functions = _convert_tools_to_gigachat_format(tools_specs)

    gigachat_messages = _convert_messages_to_gigachat_format(messages)

    steps = []

    for step_idx in range(max_steps):
        chat = Chat(
            messages=gigachat_messages,
            functions=gigachat_functions if gigachat_functions else None,
            function_call="auto" if gigachat_functions else None,
            temperature=temperature
        )

        response = client.chat(chat)
        choice = response.choices[0]
        message = choice.message

        steps.append({
            "step": step_idx,
            "finish_reason": choice.finish_reason,
            "message": {
                "role": message.role,
                "content": message.content
            }
        })

        if choice.finish_reason == "stop":
            return {
                "content": message.content,
                "steps": steps
            }

        if choice.finish_reason == "function_call":
            if not message.function_call:
                raise Exception("finish_reason=function_call но нет function_call в message")

            func_name = message.function_call.name
            func_args = message.function_call.arguments or {}

            gigachat_messages.append(
                Messages(
                    role=MessagesRole.ASSISTANT,
                    content=message.content or "",
                    function_call=FunctionCall(
                        name=func_name,
                        arguments=func_args
                    )
                )
            )

            tool_result = await execute_tool_func(func_name, func_args)

            gigachat_messages.append(
                Messages(
                    role=MessagesRole.FUNCTION,
                    name=func_name,
                    content=json.dumps(tool_result, ensure_ascii=False)
                )
            )

            continue

        if choice.finish_reason == "blacklist":
            raise Exception(f"Запрос заблокирован модерацией: {message.content}")

        if choice.finish_reason == "error":
            raise Exception("GigaChat вернул ошибку при обработке запроса")

        if choice.finish_reason == "length":
            raise Exception("Ответ обрезан по длине (превышен лимит токенов)")

        raise Exception(f"Неожиданный finish_reason: {choice.finish_reason}")

    raise Exception(f"Превышен лимит шагов tool loop: max_steps={max_steps}")


def _convert_tools_to_gigachat_format(tools_specs: list[dict[str, Any]]) -> list[Function]:
    gigachat_functions = []

    for spec in tools_specs:
        func_data = spec["function"]
        gigachat_functions.append(
            Function(
                name=func_data["name"],
                description=func_data["description"],
                parameters=FunctionParameters(**func_data["parameters"])
            )
        )

    return gigachat_functions


def _convert_messages_to_gigachat_format(messages: list[dict[str, Any]]) -> list[Messages]:
    role_map = {
        "system": MessagesRole.SYSTEM,
        "user": MessagesRole.USER,
        "assistant": MessagesRole.ASSISTANT,
        "function": MessagesRole.FUNCTION
    }

    gigachat_messages = []

    for msg in messages:
        role = role_map.get(msg.get("role", "user"), MessagesRole.USER)
        content = msg.get("content", "")

        gigachat_messages.append(
            Messages(
                role=role,
                content=content,
                function_call=msg.get("function_call")
            )
        )

    return gigachat_messages