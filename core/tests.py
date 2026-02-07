from django.core.management import call_command
from django.test import TestCase

import io


class CoreTestCase(TestCase):
    def test_no_missing_migrations(self):
        buffer = io.StringIO()
        try:
            call_command('makemigrations', check=True, dry_run=True, interactive=False, stdout=buffer)
        except SystemExit:
            self.fail(f'Missing migrations found:\n{buffer.getvalue()}')
