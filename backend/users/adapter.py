import os
from allauth.account.adapter import DefaultAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter that redirects password-reset emails
    to the frontend application instead of the backend.
    """

    def get_reset_password_from_key_url(self, key):
        """
        Override to build a frontend URL with separate uid and token.

        allauth internally creates `key` as "{uid}-{token}".
        We split on the first '-' to recover uid and token,
        then build the frontend URL.
        """
        from django.conf import settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')

        # key format is "{uid}-{token}" (see allauth password_reset.py line 110)
        # uid is the base36-encoded user PK, token is the Django token
        # The token itself contains a '-', so we split on the first '-' only
        uid, token = key.split("-", 1)

        return f"{frontend_url}/auth/reset-password?uid={uid}&token={token}"
