"""Agent 应用级资源生命周期。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.redis.ashallow import AsyncShallowRedisSaver

from gopher_agent.core.config import Settings


class AgentConfigurationError(Exception):
    """Agent 开启但模型配置不完整。"""


@dataclass(frozen=True, slots=True)
class AgentResources:
    """在应用生命周期内共享的模型和 checkpoint 资源。"""

    model: BaseChatModel
    checkpointer: BaseCheckpointSaver[Any]
    max_iterations: int


@asynccontextmanager
async def open_agent_resources(settings: Settings) -> AsyncIterator[AgentResources]:
    """初始化异步 Redis saver 和 OpenAI-compatible chat model。"""
    api_key = settings.llm_api_key.get_secret_value()
    if not settings.llm_model or not api_key:
        raise AgentConfigurationError("LLM_MODEL 和 LLM_API_KEY 不能为空")

    async with AsyncShallowRedisSaver.from_conn_string(
        settings.redis_url,
        ttl={
            "default_ttl": settings.checkpoint_ttl_minutes,
            "refresh_on_read": True,
        },
    ) as checkpointer:
        await checkpointer.asetup()
        model = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
            timeout=settings.llm_timeout_seconds,
            streaming=True,
        )
        yield AgentResources(
            model=model,
            checkpointer=checkpointer,
            max_iterations=settings.agent_max_iterations,
        )
