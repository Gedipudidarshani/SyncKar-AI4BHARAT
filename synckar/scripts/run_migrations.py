import psycopg2
import os

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print('DATABASE_URL not found, skipping migration.')
    exit(0)

try:
    conn = psycopg2.connect(db_url)
    with open('migrations/init.sql') as f:
        conn.cursor().execute(f.read())
    conn.commit()
    print('Migration complete')
except Exception as e:
    print(f'Migration failed: {e}')
    exit(1)
