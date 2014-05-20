import secret
import MySQLdb
db = MySQLdb.connect(**secret.db_credentials)

def exec_mysql(sql):
    cur = db.cursor()
    cur.execute(sql)
    rows = [r for r in cur.fetchall()]
    cur.close()
    db.commit()
    return rows