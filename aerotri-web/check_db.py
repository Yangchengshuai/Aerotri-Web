import sqlite3

conn = sqlite3.connect('data/aerotri.db')
cursor = conn.cursor()

# Check how many blocks exist
cursor.execute('SELECT COUNT(*) FROM blocks')
total = cursor.fetchone()[0]
print(f'Total blocks in database: {total}')

# Get list of blocks
cursor.execute('SELECT id, name, status FROM blocks')
print('\nBlocks:')
for row in cursor.fetchall():
    print(f'  {row[0]} - {row[1]} - {row[2]}')

conn.close()
