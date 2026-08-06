import environ as django_environ
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

import re
from pathlib import Path

from core.db import get_db_connection_app_name

env = django_environ.Env()
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env('APP_SECRET_KEY', default='d283cf4fb4ca8b1aeec08a5eaa8f0bb4')

DEBUG = env.bool('APP_DEBUG', default=False)

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # own
    'api.assessment',
    'api.llm',
    'api.user',
    'bot',
]

MIDDLEWARE = [
    'core.middleware.HealthCheckMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

AUTH_USER_MODEL = 'user.User'

TEST_RUNNER = 'core.utils_tests.TestRunner'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Feature vars

FEATURE_SENTRY = env.bool('APP_FEATURE_SENTRY', default=True)


# Proxy-related settings

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Database

DATABASES = {
    'default': env.db('APP_DB_URL', default='postgres://localhost', engine='django.db.backends.postgresql'),
}
DATABASES['default']['CONN_MAX_AGE'] = 60 * 5
database_options = DATABASES['default'].get('OPTIONS') or {}
database_options['application_name'] = get_db_connection_app_name()
DATABASES['default']['OPTIONS'] = database_options


# Cache and session

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

SESSION_COOKIE_AGE = env.int('APP_SESSION_AGE', default=3600 * 10)


# Storages

STORAGES = {
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Bot

BOT_TOKEN = env('APP_BOT_TOKEN', default='token')
BOT_PAGE_SIZE = 25


# Integrations

OPENROUTER_URL = env('APP_OPENROUTER_URL', default='https://openrouter')
OPENROUTER_API_KEY = env('APP_OPENROUTER_API_KEY', default='key')
OPENROUTER_MODEL = env('APP_OPENROUTER_MODEL', default='model')

OMDB_URL = env('APP_OMDB_URL', default='https://omdb')
OMDB_API_KEY = env('APP_OMDB_API_KEY', default='key')


# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'core.logging.formatters.JSONFormatter',
        },
    },
    'filters': {
        'health-check-ignore': {
            '()': 'core.logging.filters.HealthCheckIgnoreFilter',
        },
    },
    'handlers': {
        'console': {
            '()': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'gunicorn.access': {
            'handlers': ['console'],
            'filters': ['health-check-ignore'],
            'level': 'INFO',
            'propagate': False,
        },
        'gunicorn.error': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'httpx2': {
            'level': 'WARNING',
        },
    },
}


# Internationalization

LANGUAGES = (('en', 'English'),)

LANGUAGE_CODE = 'en'

USE_I18N = False

TIME_ZONE = 'UTC'

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'


# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Sentry

if FEATURE_SENTRY:
    SENTRY_DSN = env('APP_SENTRY_DSN', default='')
    SENTRY_SAMPLE_RATE = env.float('APP_SENTRY_SAMPLE_RATE', default=0.5)
    sentry_sampler_exclude_regex = re.compile(rf'(/liveness|/readiness|/admin|{STATIC_URL})')

    def sentry_traces_sampler(context: dict) -> float:
        """Determine sample rate based on transaction context."""

        path_info = context.get('wsgi_environ', {}).get('PATH_INFO')
        if not path_info:
            path_info = context.get('asgi_scope', {}).get('path')
        if path_info and re.match(sentry_sampler_exclude_regex, path_info):
            return 0
        return SENTRY_SAMPLE_RATE

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment='dev',
        send_default_pii=True,
        traces_sampler=sentry_traces_sampler,
        integrations=[
            DjangoIntegration(),
        ],
    )
else:
    sentry_sdk.init(dsn='')
