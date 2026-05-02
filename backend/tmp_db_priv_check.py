import os
from dotenv import load_dotenv
import psycopg2

load_dotenv('.env')
u=os.getenv('DB_USER')
p=os.getenv('DB_PASSWORD')
d=os.getenv('DB_NAME')
h=os.getenv('DB_HOST')
port=os.getenv('DB_PORT')

conn=psycopg2.connect(dbname=d,user=u,password=p,host=h,port=port)
cur=conn.cursor()
cur.execute('select current_user, session_user')
print('current_user,session_user=', cur.fetchone())
cur.execute("select tableowner from pg_tables where schemaname='public' and tablename='users_chatsession'")
print('tableowner=', cur.fetchone())
cur.execute("select has_table_privilege(current_user, 'public.users_chatsession', 'INSERT')")
print('can_insert=', cur.fetchone())
cur.close(); conn.close()
