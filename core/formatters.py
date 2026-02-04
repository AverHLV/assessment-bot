import datetime
import json
import logging
from decimal import Decimal
from uuid import UUID


class ExtendedJSONEncoder(json.JSONEncoder):
    datetime_format = '%Y-%m-%dT%H:%M:%S.%fZ'
    date_format = '%Y-%m-%d'
    time_format = '%H:%M:%S.%fZ'

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime(self.datetime_format)

        if isinstance(obj, datetime.date):
            return obj.strftime(self.date_format)

        if isinstance(obj, datetime.time):
            return obj.strftime(self.time_format)

        if isinstance(obj, datetime.timedelta | Decimal | UUID):
            return str(obj)

        return super().default(obj)


class JSONFormatter(logging.Formatter):
    """
    A logging formatter that outputs logs as JSON.

    - extra fields can be provided to the result JSON. For example, 'user_id' and 'role':
        logger.info('User logged in', extra={'fields': {'user_id': 123, 'role': 'admin'}})
    - can serialize additional types (e.g., `datetime`, `Decimal`, `UUID`, etc.).
    """

    default_time_format = '%Y-%m-%dT%H:%M:%S'
    default_msec_format = '%s.%03dZ'
    encoder_class = ExtendedJSONEncoder

    @staticmethod
    def record_to_dict(record: logging.LogRecord) -> dict:
        record_dict = {
            'timestamp': record.asctime,
            'log_level': record.levelname.lower(),
            'log_message': record.message,
        }
        if record.exc_info:
            record_dict['log_message'] = str(record.exc_info[1])
            record_dict['traceback'] = record.exc_text

        if extra_fields := record.__dict__.get('fields'):
            overwrite_keys = set(extra_fields.keys()) & set(record_dict.keys())
            if overwrite_keys:
                raise KeyError(f'Extra fields found to overwrite original log record: {", ".join(overwrite_keys)}')
            record_dict.update(extra_fields)

        return record_dict

    def dumps(self, record_dict: dict) -> str:
        return json.dumps(record_dict, cls=self.encoder_class)

    def usesTime(self) -> bool:
        return True

    def formatMessage(self, record: logging.LogRecord) -> str:
        return ''

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.stack_info:
            record.stack_info = self.formatStack(record.stack_info)

        record_dict = self.record_to_dict(record)
        return self.dumps(record_dict)
