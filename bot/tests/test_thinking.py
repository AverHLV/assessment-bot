from django.test import SimpleTestCase

from asgiref.sync import async_to_sync

import asyncio
from contextlib import suppress
from unittest.mock import AsyncMock, call, patch

from bot.thinking import ThinkingRegistry


class ThinkingRegistryTestCase(SimpleTestCase):
    registry_class = ThinkingRegistry

    def setUp(self):
        self.interaction = AsyncMock()
        self.registry = self.registry_class()

    async def test__thinking_registry__start_task(self):
        field = 'value'
        task_cancel_event = task_kwargs = None

        async def task(cancel_event: asyncio.Event, **kwargs) -> None:
            nonlocal task_cancel_event
            nonlocal task_kwargs
            task_cancel_event = cancel_event
            task_kwargs = kwargs

        with suppress(ValueError):
            async with self.registry.start_task(task, field=field) as task:
                raise ValueError('error')

        self.assertIsInstance(task, self.registry.task_class)
        self.assertTrue(task.task_id)
        self.assertNotIn(task.task_id, self.registry._tasks)
        self.assertTrue(task.task.done())
        self.assertTrue(task.cancel_event.is_set())
        self.assertIs(task.cancel_event, task_cancel_event)
        self.assertIsInstance(task_kwargs, dict)
        self.assertDictEqual(task_kwargs, {'field': field})

    async def test__thinking_registry__start_task__errors__wrong_function(self):
        with self.assertRaises(ValueError) as manager:
            async with self.registry.start_task(lambda x: x):
                pass

        self.assertTrue(str(manager.exception).startswith('The given function should be a coroutine function'))

    async def test__thinking_registry__run_task__timeout(self):
        async def task():
            await asyncio.sleep(1)

        try:
            await self.registry._run_task(task(), timeout=0.001)
        except Exception as exc:
            self.fail(f'Unexpected exception occurred: {exc}')

    async def test__thinking_registry__run_task__error(self):
        async def task():
            raise ValueError('error')

        try:
            await self.registry._run_task(task(), timeout=None)
        except Exception as exc:
            self.fail(f'Unexpected exception occurred: {exc}')

    @patch('bot.thinking.asyncio.sleep')
    @async_to_sync
    async def test__thinking_registry__tasks__show_thinking_with_loop(self, sleep_mock):
        delay = 2
        call_index = 0
        stop_index = 3
        cancel_event = asyncio.Event()

        def sleep_side_effect(*_args) -> None:
            nonlocal call_index
            call_index += 1
            if call_index == stop_index:
                cancel_event.set()

        sleep_mock.side_effect = sleep_side_effect

        await self.registry.show_thinking_with_loop(self.interaction, cancel_event, delay=delay)

        self.assertEqual(call_index, stop_index)
        self.assertEqual(self.interaction.edit_original_response.call_count, call_index)
        calls = [call(content=message) for message in self.registry.messages_thinking[:call_index]]
        self.interaction.edit_original_response.assert_has_calls(calls)

        self.assertEqual(sleep_mock.call_count, call_index)
        calls = [call(delay)] * call_index
        sleep_mock.assert_has_calls(calls)
