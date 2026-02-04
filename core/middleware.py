from django.db import connection
from django.http import HttpResponse, HttpResponseServerError

import logging

logger = logging.getLogger(__name__)


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        match request.path.rstrip('/'):
            case '/liveness':
                return self.liveness()
            case '/readiness':
                return self.readiness()
            case _:
                return self.get_response(request)

    @staticmethod
    def liveness():
        return HttpResponse('OK')

    def readiness(self):
        if not self.check_db():
            return HttpResponseServerError('The app is not ready')
        return HttpResponse('OK')

    @staticmethod
    def check_db() -> bool:
        try:
            with connection.temporary_connection() as cursor:
                cursor.execute('SELECT 1')
            return True
        except Exception as ex:
            logger.exception(ex)
            return False
