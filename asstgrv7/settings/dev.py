from pathlib import Path
import os
from dotenv import load_dotenv
from django.urls import reverse_lazy
load_dotenv()
import os




BASE_DIR = Path(__file__).resolve().parent.parent

AUTH_USER_MODEL = 'users.CustomUser'

LOGIN_URL = '/admin/login/'
# SSecurity
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
DEBUG = True  


ALLOWED_HOSTS = [ '127.0.0.1', 'localhost']

# Installed apps
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Django modules
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',

    # Your apps
    'api_management',
    'users.apps.UsersConfig',
    'api_public',


    
]


# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'asstgrv7.urls'

# Templates
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

# ASGI / Channels
ASGI_APPLICATION = 'asstgrv7.asgi.application'

# DATABASE
USE_POOLER = os.getenv('USE_POOLER', 'true').lower() == 'true'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME_local'),
        'USER': os.getenv('DB_USER_local'),
        'PASSWORD': os.getenv('DB_PASSWORD_local'),
        'HOST': os.getenv('DB_HOST_local') ,
        'PORT': os.getenv('DB_PORT_local') ,
        'OPTIONS': {
            'sslmode': 'require',
        }
    }
}


# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    'DEFAULT_THROTTLE_CLASSES': [
    'api_public.throttling.APIKeyBurstThrottle',
    'api_public.throttling.APIKeySustainedThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'api_burst': '30/second',
        'api_sustained': '1000/day',
    },
}

SIMPLE_JWT = {
    'BLACKLIST_AFTER_ROTATION': True,
    'ROTATE_REFRESH_TOKENS': True,
}


# Auth password validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Language / Time
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JS, etc.)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR.parent / 'users' / 'static',
]

MEDIA_URL = '/media/' 


# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ULT_AUTO_FIELD = 'django.db.models.BigAutoField'


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)
