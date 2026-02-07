from django.test import SimpleTestCase

from core.logging.filters import HealthCheckIgnoreFilter
from core.utils_tests import get_log_record


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
