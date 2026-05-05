from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_fix_chat_created_at_defaults"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE public.users_chatsession
                  ALTER COLUMN created_at SET DEFAULT now();

                ALTER TABLE public.users_chatmessage
                  ALTER COLUMN created_at SET DEFAULT now();
            """,
            reverse_sql="""
                ALTER TABLE public.users_chatsession
                  ALTER COLUMN created_at DROP DEFAULT;

                ALTER TABLE public.users_chatmessage
                  ALTER COLUMN created_at DROP DEFAULT;
            """,
        ),
    ]
