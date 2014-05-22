import gmail # https://github.com/charlierguo/gmail
import sys
import secret
import datetime
from util import exec_mysql
from itertools import chain

def get_start_date():
    dates = list(exec_mysql('SELECT max(ping), max(pong) FROM portals2;')[0])
    dates.append(datetime.datetime(2012, 11, 15)) # closed beta begin date
    dates = filter(lambda x: bool(x), dates)
    if len(dates) > 1:
        return max(dates)
    else:
        return dates[0]

def scrape():
    username = secret.your_email
    password = secret.email_password

    pings = ('Ingress Portal Submitted',)
    pongs = ('Ingress Portal Live',
             'Ingress Portal Rejected',
             'Ingress Portal Duplicate',
             'Ingress Portal Game Rejected',)

    start_date = get_start_date()

    print 'logging into %s@gmail.com' % username
    g = gmail.login(username, password)
    if not g.logged_in:
        print 'login failed'
        sys.exit(1)
    print "we're in"
    emails = []
    emails.extend(g.inbox().mail(sender='super-ops@google.com', after=start_date.date()))
    emails.extend(g.inbox().mail(sender='ingress-support@google.com', after=start_date.date()))

    if len(emails): print 'emails found. proccessing...'
    else: print 'no new emails found'
    length_before = exec_mysql('SELECT count(*) FROM portals2')[0][0]
    print length_before 

    for message in emails:
        message.fetch()
        subject = message.subject
        print subject

        if ':' in subject and 'Ingress Portal' in subject:
            preamble, portal_name = subject.partition(':')[::2]
            portal_name = portal_name.lower().strip()
            date = message.sent_at

            if preamble in pings and date not in set(chain(*exec_mysql('SELECT ping FROM portals2'))):
                print 'new submitted portal'
                url = message.html.partition('src="')[2].partition('" alt="')[0]
                exec_mysql("""INSERT INTO portals2 (ping, `name`, image_url) VALUES ('%s', "%s", '%s') ON DUPLICATE KEY UPDATE image_url='%s';""" % (date, portal_name.replace('"', '\\"'), url, url))

            if preamble in pongs and date not in set(chain(*exec_mysql('SELECT pong FROM portals2'))):
                status = ('Live' in preamble)
                names = list(chain(*exec_mysql('SELECT `name` FROM portals2 WHERE status is null;')))
                if names.count(portal_name) == 1:
                    print 'portal response received'
                    exec_mysql("""UPDATE portals2 SET pong = '%s', `status` = %s WHERE `name` = "%s" AND status is null LIMIT 1;""" % (date, status, portal_name.replace('"', '\\"')))
                else:
                    print 'duplicate or modified name; attention required'
                    exec_mysql("""INSERT INTO portals2 (pong, `name`, `status`) VALUES ('%s', "%s", %s) ON DUPLICATE KEY UPDATE Id=Id;""" % (date, portal_name.replace('"', '\\"'), status))

    print 'done'
    g.logout()
    print 'logged out'

    length_after = exec_mysql('SELECT count(*) FROM portals2')[0][0]
    if length_after == length_before:
        print 'no change'
    print 'all done'

if __name__ == '__main__':
    scrape()