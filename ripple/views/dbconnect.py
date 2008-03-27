"DB connect string for making other connections."

from django.conf import settings

DSN = 'dbname=%s' % settings.DATABASE_NAME
if settings.DATABASE_USER:
    DSN += ' user=%s' % settings.DATABASE_USER
if settings.DATABASE_PASSWORD:
    DSN += ' password=%s' % settings.DATABASE_PASSWORD
if settings.DATABASE_HOST:
    DSN += ' host=%s' % settings.DATABASE_HOST
if settings.DATABASE_PORT:
    DSN += ' port=%s' % settings.DATABASE_PORT

