"""Constants for the auth module."""
from datetime import timedelta

ACCESS_TOKEN_EXPIRATION = timedelta(minutes=30)

GROUP_ID_ADMIN = 'system-admin'
GROUP_ID_USER = 'system-users'
GROUP_ID_READ_ONLY = 'system-read-only'
