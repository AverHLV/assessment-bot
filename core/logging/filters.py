import logging


class HealthCheckIgnoreFilter(logging.Filter):
    record_parts = 'GET /liveness', 'GET /readiness'

    def filter(self, record: logging.LogRecord) -> bool:
        if not super().filter(record):
            return False

        record.message = record.getMessage()
        return not any(part in record.message for part in self.record_parts)
