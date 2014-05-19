import gmail # https://github.com/charlierguo/gmail
import sys
import secret
import datetime

import MySQLdb
db = MySQLdb.connect(**secret.db_credentials)

def exec_mysql(sql):
    cur = db.cursor()
    cur.execute(sql)
    rows = [r for r in cur.fetchall()]
    cur.close()
    db.commit()
    return rows

def scrape():
    username = secret.your_email
    password = secret.email_password

    pings = ('Ingress Portal Submitted',)
    pongs = ('Ingress Portal Live',
             'Ingress Portal Rejected',
             'Ingress Portal Duplicate',
             'Ingress Portal Game Rejected',)

    last_run = max([d for d in exec_mysql('SELECT max(ping), max(pong) FROM portals2;')[0] if d])
    if not last_run: last_run = datetime.datetime(2012, 11, 15) # closed beta begin date
    data = exec_mysql('SELECT ping, pong, `name`, `status` FROM portals2;')

    print 'logging into %s@gmail.com' % username
    g = gmail.login(username, password)
    if not g.logged_in:
        print 'login failed'
        sys.exit(1)
    print "we're in"
    emails = []
    emails.extend(g.inbox().mail(sender='super-ops@google.com', after=last_run.date()))
    emails.extend(g.inbox().mail(sender='ingress-support@google.com', after=last_run.date()))

    if len(emails): print 'emails found. proccessing...'
    else: print 'no new emails found'
    length_before = len(data)
    print length_before 

    for message in emails:
        message.fetch()
        subject = message.subject
        print subject

        if ':' in subject and 'Ingress Portal' in subject:
            preamble, portal_name = subject.partition(':')[::2]
            portal_name = portal_name.lower().strip().replace("'", "\\'")
            date = str(message.sent_at)

            if preamble in pings and date not in zip(*data)[0]:
                print 'new submitted portal'
                url = message.html.partition('src="')[2].partition('" alt="')[0]
                exec_mysql("INSERT INTO portals2 (ping, `name`, image_url) VALUES ('%s', '%s', '%s') ON DUPLICATE KEY UPDATE image_url='%s';" % (date, portal_name, url, url))
                data = exec_mysql('SELECT ping, pong, `name`, `status` FROM portals2;') # refresh data in case we get a response on this run too
 
            if preamble in pongs and date not in zip(*data)[1]:
                status = 'Live' in preamble
                dangling_data = exec_mysql('SELECT ping, pong, `name`, `status` FROM portals2 WHERE status is null;')
                names = zip(*dangling_data)[2]
                if names.count(portal_name) == 1:
                    print 'portal response received'
                    exec_mysql("UPDATE portals2 SET pong = '%s', `status` = %s WHERE `name` = '%s AND status is null LIMIT 1';" % (date, status, portal_name))
                else:
                    print 'duplicate or modified name; attention required'
                    exec_mysql("INSERT INTO portals2 (pong, `name`, `status`) VALUES ('%s', '%s', %s) ON DUPLICATE KEY UPDATE Id=Id;" % (date, portal_name, status))

    print 'done'
    g.logout()
    print 'logged out'

    length_after = len(data)
    if length_after == length_before:
        print 'no change'
    print 'all done'

if __name__ == '__main__':
    scrape()