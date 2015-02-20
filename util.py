import secret
import MySQLdb

class CM(object):
    ''' connection manager '''
    def __init__(self, credentials):
        self.connection = None
        self.credentials = credentials

    def set_credentials(self, credentials):
        self.credentials = credentials
        self.close()

    def get_conn(self):
        if not self.connection:
            self.connection = MySQLdb.connect(**self.credentials)
        return self.connection

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

cm = CM(secret.db_credentials) # default so I don't have to fix my old code :P

def exec_mysql(sql, retries=2):
    try:
        cur = None # needed in case get_conn() dies
        db = cm.get_conn()
        cur = db.cursor()
        cur.execute(sql)
        rows = [r for r in cur.fetchall()]
        cur.close()
        db.commit()
        return rows

    except MySQLdb.OperationalError as exc:
        if cur:
            cur.close()
        cm.close()
        if retries:
            return exec_mysql(sql, retries-1)
        else:
            raise
