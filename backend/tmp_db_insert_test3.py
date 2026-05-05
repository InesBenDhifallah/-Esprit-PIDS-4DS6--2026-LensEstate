import os
from dotenv import load_dotenv
import psycopg2

load_dotenv('.env')
conn=psycopg2.connect(dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'))
cur=conn.cursor()
cur.execute("""
select table_name, column_default
from information_schema.columns
where table_schema='public' and table_name in ('users_chatsession','users_chatmessage')
  and column_name='created_at'
order by table_name
""")
for row in cur.fetchall():
    print(row)

cur.execute("insert into users_chatsession (session_id, title) values ('test-session-priv3', 't') returning id, created_at")
print('inserted', cur.fetchone())
conn.rollback()
cur.close(); conn.close()
