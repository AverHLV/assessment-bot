from django.test import override_settings
from django.test.runner import DiscoverRunner

import sentry_sdk
from httpx import Request, Response

import logging
from collections.abc import Callable
from http import HTTPStatus


def get_log_record(**kwargs) -> logging.LogRecord:
    data = {
        'msg': 'message',
        'levelname': logging.getLevelName(logging.INFO),
        **kwargs,
    }
    return logging.makeLogRecord(data)


def get_httpx_test_response(
    status_code: int = HTTPStatus.NOT_FOUND,
    content: bytes = None,
    text: str = None,
    body: dict | list = None,
) -> Response:
    request = Request(method='GET', url='http://test')
    return Response(status_code=status_code, content=content, text=text, json=body, request=request)


def pause_date_auto_fields(fields: list) -> Callable:
    """
    Disable the "auto_*" options for specified date and time fields
    and allows the desired values to be set while the factory instantiates the model. For testing purposes only.
    """

    def decorator(func):
        def wrapper(cls, model_class, *args, **kwargs):
            auto_now_fields, auto_now_add_fields = [], []
            for field in fields:
                if field not in kwargs:
                    continue
                model_field = model_class._meta.get_field(field)
                if getattr(model_field, 'auto_now', False):
                    model_field.auto_now = False
                    auto_now_fields.append(model_field)
                elif getattr(model_field, 'auto_now_add', False):
                    model_field.auto_now_add = False
                    auto_now_add_fields.append(model_field)

            obj = func(cls, model_class, *args, **kwargs)

            for model_field in auto_now_fields:
                model_field.auto_now = True
            for model_field in auto_now_add_fields:
                model_field.auto_now_add = True
            return obj

        return wrapper

    return decorator


class TestRunner(DiscoverRunner):
    def run_tests(self, test_labels, **kwargs):
        logging.disable(logging.CRITICAL)
        sentry_sdk.init()  # disable events capturing
        test_password_hashers = ['django.contrib.auth.hashers.MD5PasswordHasher']
        with override_settings(PASSWORD_HASHERS=test_password_hashers):
            return super().run_tests(test_labels, **kwargs)
