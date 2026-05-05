import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lenstate.settings')
django.setup()

from users.models import ChatSession

try:
    session, created = ChatSession.objects.get_or_create(session_id="123", defaults={"title": "test"})
    print("SUCCESS", session)
except Exception as e:
    print("ERROR", e)
