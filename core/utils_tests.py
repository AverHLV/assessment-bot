from django.test import override_settings
from django.test.runner import DiscoverRunner

import sentry_sdk

import logging


def get_log_record(**kwargs) -> logging.LogRecord:
    data = {
        'msg': 'message',
        'levelname': logging.getLevelName(logging.INFO),
        **kwargs,
    }
    return logging.makeLogRecord(data)


class TestRunner(DiscoverRunner):
    def run_tests(self, test_labels, **kwargs):
        logging.disable(logging.CRITICAL)
        sentry_sdk.init()  # disable events capturing
        test_password_hashers = ['django.contrib.auth.hashers.MD5PasswordHasher']
        with override_settings(PASSWORD_HASHERS=test_password_hashers):
            return super().run_tests(test_labels, **kwargs)
