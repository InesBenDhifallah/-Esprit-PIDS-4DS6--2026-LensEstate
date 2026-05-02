import os
from dotenv import load_dotenv
import psycopg2

load_dotenv('.env')
conn=psycopg2.connect(dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'))
cur=conn.cursor()
cur.execute("insert into users_chatsession (session_id, title) values ('test-session-priv2', 't') returning id, created_at")
print('inserted', cur.fetchone())
conn.rollback()
cur.close(); conn.close()
