# Django settings for django project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Your Name', 'whoever@gmail.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'postgresql'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'ripplesite'             # Or path to database file if using sqlite3.
DATABASE_USER = 'whoever'             # Not used with sqlite3.
DATABASE_PASSWORD = 'somepassword'         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.


# Local time zone for this installation. All choices can be found here:
# http://www.postgresql.org/docs/current/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = '/home/thartman/ripplesite/ripple/media/'

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = '/media'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
# as far as I understand, the secret key gets created along with some other stuff when yu run
# python django-admin.py startproject ripplesite
SECRET_KEY = 'secret holy gibberish which gets generated when you create a django project'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.middleware.doc.XViewMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
)

ROOT_URLCONF = 'ripplesite.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates".
    # Always use forward slashes, even on Windows.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'ripplesite.ripple',
    'ripplesite.market',
    'django.contrib.admin',
)

# for sending out automated email messages
EMAIL_HOST = '' # set to 'TEST_DEBUG' to fake it
EMAIL_HOST_USER = '' # leave blank if not required by host
EMAIL_HOST_PASSWORD = '' # leave blank if not required by host

# for auto-populating DjangoContext object
# see http://www.djangoproject.com/documentation/settings/#template-context-processors
TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug", # optional
    "django.core.context_processors.i18n", # optional
    "ripplesite.ripple.views.userNode_proc", # populates context with logged-in user ID
    "ripplesite.ripple.views.siteInfo_proc", # populates context with site name, service name, admin name & email 
    "ripplesite.ripple.views.userAgent_proc", # makes sure good browsers get the good logo
)

SESSION_COOKIE_AGE = 600 # session expiry time, in seconds

SITE_NAME = '' # the domain name for your Ripple site, eg, 'ripplepay.com'
SERVICE_NAME = '' # the name of your Ripple service, eg, 'RipplePay'

# this is the intro paragraph for the front page.  you can put html in here (it gets wrapped in a <p>).
HOME_INTRO_TEXT = "Welcome to my ripple site!"
