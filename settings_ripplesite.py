# In addition to regular Django settings, 
# these fields must be set in your settings.py for RippleSite to work:

ADMINS = (
    ('Your Name', 'your_email@domain.com'), # set your own name and email address - used for contact page etc.
)

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
# Needed for ripplesite to display media when running on the django development server
MEDIA_ROOT = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/admin/", "/media/admin/".
ADMIN_MEDIA_PREFIX = ''  # something different than '/media/'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
)

ROOT_URLCONF = 'ripplesite.urls'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
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

SESSION_COOKIE_AGE =  # session expiry time, in seconds

SITE_NAME = '' # the domain name for your Ripple site, eg, 'ripplepay.com'
SERVICE_NAME = '' # the name of your Ripple service, eg, 'RipplePay'

# this is the intro paragraph for the front page.  you can put html in here (it gets wrapped in a <p>).
HOME_INTRO_TEXT = "Welcome to my RippleSite!"
