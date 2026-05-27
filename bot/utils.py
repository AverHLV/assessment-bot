from django.db import connections

from asgiref.sync import sync_to_async


def close_all_db_connections() -> None:
    connections.close_all()


aclose_all_db_connections = sync_to_async(close_all_db_connections, thread_sensitive=True)
