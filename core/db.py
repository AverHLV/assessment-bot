import sys


def get_db_connection_app_name(prefix: str = 'assessment-bot') -> str:
    if sys.argv[0].endswith('manage.py'):
        return f'{prefix}-{sys.argv[1]}'

    return f'{prefix}-app'
