import discord

import asyncio
import logging
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class ThinkingTask:
    task_id: str
    task: asyncio.Task
    cancel_event: asyncio.Event

    async def finalize(self) -> None:
        self.cancel_event.set()
        await self.task


class ThinkingRegistry:
    task_class = ThinkingTask

    message_thinking = "Please wait... I'm gently sifting through fading memories."
    messages_thinking = (
        f'{message_thinking}.',
        f'{message_thinking}..',
        f'{message_thinking} The past refuses to stay buried...',
        f'{message_thinking} These memories, they hurt...',
        f'{message_thinking} Ah! A beautiful pattern emerges!',
        f"{message_thinking} No, it's gone... like everything else...",
        f'{message_thinking} Your tastes clash like rival protagonists!',
        f"{message_thinking} This tension... it's almost romantic...",
        f'{message_thinking} This is peak drama!',
        f'{message_thinking} Or... maybe just confusion...',
        f"{message_thinking} Wait-wait!! It's almost complete!",
        f'{message_thinking} ...No. I was mistaken.',
        f'{message_thinking} Everything decays, even conclusions...',
    )

    def __init__(self):
        self._tasks: dict[str, ThinkingRegistry.task_class] = {}

    @asynccontextmanager
    async def start_task(self, func: Callable, timeout: float | None = 60, **kwargs) -> AsyncIterator[task_class]:
        if not asyncio.iscoroutinefunction(func):
            raise ValueError(f'The given function should be a coroutine function: {func}')

        kwargs.setdefault('cancel_event', asyncio.Event())
        coro = self._run_task(func(**kwargs), timeout=timeout)
        task = asyncio.create_task(coro)
        thinking_task = self.task_class(
            task_id=str(uuid4()),
            task=task,
            cancel_event=kwargs['cancel_event'],
        )
        self._tasks[thinking_task.task_id] = thinking_task
        task.add_done_callback(lambda _, th_task_id=thinking_task.task_id: self._tasks.pop(th_task_id, None))

        try:
            yield thinking_task
        finally:
            await thinking_task.finalize()

    @staticmethod
    async def _run_task(coro: Coroutine, timeout: float | None) -> None:
        try:
            async with asyncio.timeout(timeout):
                await coro
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            pass
        except Exception as exc:
            logger.exception(exc)

    async def show_thinking(self, interaction: discord.Interaction, edit: bool = False) -> None:
        if edit:
            await interaction.response.edit_message(content=self.message_thinking, embed=None, view=None)
        else:
            await interaction.response.send_message(content=self.message_thinking, ephemeral=True)

    # tasks

    async def show_thinking_with_loop(
        self,
        interaction: discord.Interaction,
        cancel_event: asyncio.Event,
        delay: float = 1,
    ) -> None:
        """Show thinking loop with progress messages. Should be started only after the 'show_thinking' method call."""

        i = 0
        while not cancel_event.is_set():
            message = self.messages_thinking[i % len(self.messages_thinking)]
            await interaction.edit_original_response(content=message)
            await asyncio.sleep(delay)
            i += 1


thinking_registry = ThinkingRegistry()
