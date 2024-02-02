"""
Django settings for absklad_commerce project.

Generated by 'django-admin startproject' using Django 4.2.7.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""
import os
from datetime import timedelta
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', cast=bool)
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', cast=list)
CORS_ALLOW_ALL_ORIGINS = True

# Application definition

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework_simplejwt',
    'rest_framework',
    'drf_yasg',
    'drf_spectacular',
    'corsheaders',
    'django_filters',
    'django_celery_beat',

    'mongo_logger',
    'account',
    'one_c',
    'general_service',
    'product',
    'order',
    'promotion',
    'chat',
    'crm_general',
    'crm_stat',
    'crm_kpi',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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


ROOT_URLCONF = 'absklad_commerce.urls'

WSGI_APPLICATION = 'absklad_commerce.wsgi.application'
ASGI_APPLICATION = "absklad_commerce.asgi.application"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST'),
        'PORT': config('POSTGRES_PORT', cast=int)
    }
}

REDIS_HOST = config("REDIS_HOST", default='localhost')
REDIS_PASSWORD = config("REDIS_PASSWORD", default='')
REDIS_PORT = config("REDIS_PORT", default=6379)
REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/'

CACHES = {
    'default': {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL + '0',
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL + '1'],
            "symmetric_encryption_keys": [SECRET_KEY],
        },
    },
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'AsiaBrand Commerce Project API',
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}


BROKER_URL = REDIS_URL + '0'
CELERY_RESULT_BACKEND = BROKER_URL


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Asia/Bishkek'

USE_I18N = True
USE_L10N = True
USE_TZ = True
USE_DEPRECATED_PYTZ = True

STATIC_URL = '/static-files/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media-files/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'account.MyUser'

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    "COERCE_DECIMAL_TO_STRING": False,

}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': False,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
    "TOKEN_OBTAIN_SERIALIZER": "account.serializers.UserLoginSerializer",
}

# Logging
# MONGO_DB_CONNECTION_URL = config('MONGO_DB_CONNECTION_URL')
# LOG_MONGO_DATABASE_NAME = config('LOG_MONGO_DATABASE_NAME')
# LOG_MONGO_COLLECTION_NAME = config('LOG_MONGO_COLLECTION_NAME')
#
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#
#     'filters': {
#         'require_debug_false': {
#             '()': 'django.utils.log.RequireDebugFalse',
#         },
#         'require_debug_true': {
#             '()': 'django.utils.log.RequireDebugTrue',
#         },
#     },
#     'formatters': {
#         'console': {'format': '%(levelname)s | %(asctime)s | %(module)s | %(message)s'}
#     },
#     'handlers': {
#         'mongolog': {
#             'level': 'INFO',
#             'class': 'mongo_logger.handlers.CustomMongoLogHandler',
#             'connection': MONGO_DB_CONNECTION_URL,
#             'collection': LOG_MONGO_COLLECTION_NAME,
#             'database': LOG_MONGO_DATABASE_NAME
#         },
#         'console': {
#             'level': 'INFO',
#             'class': 'logging.StreamHandler',
#             'formatter': 'console'
#         },
#         'mail_admins': {
#             'level': 'ERROR',
#             'filters': ['require_debug_false'],
#             'class': 'django.utils.log.AdminEmailHandler',
#             'include_html': True,
#         }
#     },
#     'loggers': {
#         '': {
#             'handlers': ['mongolog', 'console'],
#             'level': 'INFO',
#             'propagate': True
#         },
#         'statistics': {
#             'handlers': ['mongolog', 'console'],
#             'level': 'INFO',
#             'propagate': True
#         },
#         'tasks_management': {
#             'handlers': ['mongolog', 'console'],
#             'level': 'INFO',
#             'propagate': False
#         },
#         'django': {
#             'handlers': ['console', 'mongolog'],
#             'level': 'INFO',
#             'propagate': False,
#         },
#         'django.server': {
#             'handlers': ['console', 'mongolog'],
#             'level': 'INFO',
#             'propagate': False,
#         },
#         'django.request': {
#             'handlers': ['console', 'mongolog'],
#             'level': 'ERROR',
#             'propagate': False,
#         },
#         'django.security': {
#             'handlers': ['mail_admins', 'console', 'mongolog'],
#             'level': 'ERROR',
#             'propagate': False,
#         }
#     },
# }

KPI_CHECK_MONTHS = 3
KPI_INCREASE_THRESHOLD = 0.2

SERVER_URL = "http://81.31.197.124/"

DATA_UPLOAD_MAX_NUMBER_FIELDS = 3000000
