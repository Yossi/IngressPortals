import pymysql # pip install pymysql
pymysql.install_as_MySQLdb()
import MySQLdb
import logging

import warnings
warnings.filterwarnings('error', category=MySQLdb.Warning)

class CM(object):
    ''' connection manager '''
    def __init__(self):
        self.connection = None

    def set_credentials(self, credentials):
        self.credentials = credentials
        self.close()

    def get_conn(self):
        if not self.connection:
            logging.info('no db connection. creating...')
            self.connection = MySQLdb.connect(**self.credentials)
        return self.connection

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

cm = CM()

def exec_mysql(sql, retries=2):
    try:
        cur = None # needed in case get_conn() dies
        db = cm.get_conn()
        cur = db.cursor()
        cur.execute(sql)
        rows = [r for r in cur.fetchall()]
        if not rows and not sql.strip().lower().startswith('select'):
            rows = cur.rowcount
        cur.close()
        db.commit()
        return rows

    except MySQLdb.OperationalError as exc:
        if cur:
            cur.close()
        cm.close()
        if retries:
            logging.warning('sql query failed, retrying')
            return exec_mysql(sql, retries-1)
        else:
            raise

    except:
        logging.error(sql)
        raise
