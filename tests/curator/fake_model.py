"""A scripted tool-calling chat model: tests never call a network model."""

from __future__ import annotations

import itertools
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

_ids = itertools.count(1)


def call(name: str, **args: Any) -> AIMessage:
    """One scripted turn that calls tool `name` with `args`."""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call-{next(_ids)}"}])


def say(text: str = "done") -> AIMessage:
    """A final turn with no tool call."""
    return AIMessage(content=text)


class ScriptedChatModel(BaseChatModel):
    """Returns the scripted messages in order, then "done". Records every prompt it was sent."""

    model_name: str = "scripted-curator"
    script: list[AIMessage] = Field(default_factory=list)
    calls: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedChatModel:
        return self

    def _generate(self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None,
                  **kwargs: Any) -> ChatResult:
        self.calls.append(list(messages))
        msg = self.script.pop(0) if self.script else say()
        return ChatResult(generations=[ChatGeneration(message=msg)])
