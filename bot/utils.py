from django.db import connections

from asgiref.sync import sync_to_async


@sync_to_async
def close_all_db_connections() -> None:
    for connection in connections.all():
        connection.close()
