import secret
import MySQLdb

class CM(object):
    def __init__(self):
        self.connection = None
        
    def get_conn(self):
        if not self.connection:
            self.connection = MySQLdb.connect(**secret.db_credentials)
        return self.connection

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

cm = CM()

def exec_mysql(sql, retries=2):
    try:
        db = cm.get_conn()
        cur = db.cursor()
        cur.execute(sql)
        rows = [r for r in cur.fetchall()]
        cur.close()
        db.commit()
        return rows
        
    except OperationalError as exc:
        if cursor:
            cursor.close()
        cm.close()
        if retries:
            return exec_mysql(sql, retries-1)
        else:
            raise
     