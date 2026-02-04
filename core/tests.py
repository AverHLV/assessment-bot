from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

import io
import json
import logging
from datetime import datetime
from decimal import Decimal

from core.filters import HealthCheckIgnoreFilter
from core.formatters import JSONFormatter
from core.utils_tests import get_log_record


class CoreTestCase(TestCase):
    def test_no_missing_migrations(self):
        buffer = io.StringIO()
        try:
            call_command('makemigrations', check=True, dry_run=True, interactive=False, stdout=buffer)
        except SystemExit:
            self.fail(f'Missing migrations found:\n{buffer.getvalue()}')


class HealthCheckIgnoreFilterTestCase(SimpleTestCase):
    filter_class = HealthCheckIgnoreFilter

    def setUp(self):
        self.filter = self.filter_class()

    def test__health_check_ignore_filter(self):
        record = get_log_record(msg='message')
        result = self.filter.filter(record)
        self.assertTrue(result)

    def test__health_check_ignore_filter__ignore(self):
        record = get_log_record(msg=self.filter.record_parts[0])
        result = self.filter.filter(record)
        self.assertFalse(result)


class JSONFormatterTestCase(SimpleTestCase):
    formatter_class = JSONFormatter

    def setUp(self):
        self.formatter = self.formatter_class()

    def assert_log_record(self, result: str, record: logging.LogRecord, exception: Exception = None) -> None:
        result = json.loads(result)
        fields = ['timestamp', 'log_level', 'log_message']
        if exception:
            fields.append('traceback')
        for field in fields:
            self.assertIn(field, result)

        self.assertEqual(result['log_level'], record.levelname.lower())

        timestamp = result['timestamp'].split('.')[0]
        timestamp = datetime.strptime(timestamp, self.formatter.default_time_format)
        timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
        expected_timestamp = datetime.now().replace(minute=0, second=0, microsecond=0)
        self.assertEqual(timestamp, expected_timestamp)

        if exception:
            self.assertEqual(result['log_message'], str(exception))
            self.assertTrue(result['traceback'])
        else:
            self.assertEqual(result['log_message'], record.message)

    def test__json_formatter_format(self):
        record = get_log_record()
        result = self.formatter.format(record)
        self.assert_log_record(result, record)

    def test__json_formatter_format__exception(self):
        try:
            raise ValueError('error')
        except ValueError as ex:
            exception = ex

        record = get_log_record(exc_info=(type(exception), exception, exception.__traceback__))
        result = self.formatter.format(record)
        self.assert_log_record(result, record, exception=exception)

    def test__json_formatter_format__extra_fields(self):
        field1 = True
        field2 = Decimal('1')
        field3 = datetime.now()
        record = get_log_record(fields={'field1': field1, 'field2': field2, 'field3': field3})
        result = self.formatter.format(record)

        self.assert_log_record(result, record)
        result_dict = json.loads(result)
        self.assertIn('field1', result_dict)
        self.assertIs(result_dict['field1'], field1)
        self.assertIn('field2', result_dict)
        self.assertEqual(result_dict['field2'], str(field2))
        self.assertIn('field3', result_dict)
        actual_field3 = datetime.strptime(result_dict['field3'], self.formatter.encoder_class.datetime_format)
        self.assertEqual(actual_field3, field3)

    def test__json_formatter_format__errors__overwrite_by_extra_fields(self):
        record = get_log_record(fields={'log_message': 'other message'})
        with self.assertRaises(KeyError) as manager:
            self.formatter.format(record)
        expected_error_msg = "'Extra fields found to overwrite original log record: log_message'"
        self.assertEqual(str(manager.exception), expected_error_msg)
