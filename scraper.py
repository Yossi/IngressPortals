import gmail # https://github.com/charlierguo/gmail
import sys
import secret
import datetime
from util import exec_mysql
from itertools import chain
import operator
from urlparse import urlsplit, urlunsplit, parse_qs
from urllib import urlencode

def get_start_date():
    dates = list(exec_mysql('SELECT max(ping), max(pong) FROM portals2;')[0])
    dates.append(datetime.datetime(2012, 11, 15)) # closed beta begin date
    dates = filter(lambda x: bool(x), dates)
    if len(dates) > 1:
        return max(dates)
    else:
        return dates[0]

def get_status(status_before, status_after):
    if status_after == status_before:
        return 'no change'
    return 'Accepted: %s Rejected: %s Pending: %s' % tuple(map(operator.__sub__, status_after, status_before))

def canonicalize_url(url):
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    query['ll'] = '%s,%s' % tuple(map(float, query['ll'][0].split(',')))
    newparts = ('https',
                parts.netloc,
                parts.path,
                'll=%(ll)s&z=17&pll=%(ll)s' % query,
                parts.fragment)
    return urlunsplit(newparts)

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
    status_before = exec_mysql('SELECT SUM(status = 1), SUM(status = 0), SUM(status IS NULL) FROM portals2')[0]

    for message in emails:
        message.fetch()
        subject = message.subject
        print subject

        if ':' in subject and 'Ingress Portal' in subject:
            preamble, portal_name = subject.partition(':')[::2]
            portal_name = portal_name.lower().strip()
            date = message.sent_at
            status = ('Live' in preamble)

            image_url = message.html.partition('src="')[2].partition('" alt="')[0]

            portal_url = message.html.partition('<a href="')[2].partition('">')[0].replace('&amp;', '&')
            portal_url = canonicalize_url(portal_url) if 'll' in portal_url else 'null'

            if preamble in pings and date not in set(chain(*exec_mysql('SELECT ping FROM portals2'))):
                print 'new submitted portal'
                exec_mysql("""INSERT INTO portals2 (ping, `name`, image_url) VALUES ('%s', "%s", '%s') ON DUPLICATE KEY UPDATE image_url='%s';""" % (date, portal_name.replace('"', '\\"'), image_url, image_url))

            if preamble in pongs and date not in set(chain(*exec_mysql('SELECT pong FROM portals2'))):
                print 'portal response received'
                names = list(chain(*exec_mysql('SELECT `name` FROM portals2 WHERE status is null;')))
                if names.count(portal_name) == 1:
                    exec_mysql("""UPDATE portals2 SET pong = '%s', `status` = %s, portal_url = '%s' WHERE `name` = "%s" AND status is null LIMIT 1;""" % (date, status, portal_url, portal_name.replace('"', '\\"')))
                else:
                    #id = exec_sql("""SELECT Id FROM portals2 WHERE image_url = '%s';""" % image_url)[0]
                    if image_url:
                        print 'attempting image_url match'
                        exec_mysql("""UPDATE portals2 SET pong = '%s', `status` = %s, portal_url = '%s' WHERE image_url = '%s' AND status is null LIMIT 1;""" % (date, status, portal_url, image_url))
                    else:
                        print 'FAILED! duplicate or modified name; attention required'
                        exec_mysql("""INSERT INTO portals2 (pong, `name`, `status`, portal_url) VALUES ('%s', "%s", %s, "%s") ON DUPLICATE KEY UPDATE Id=Id;""" % (date, portal_name.replace('"', '\\"'), status, portal_url))

    print 'done'
    g.logout()
    print 'logged out'

    status_after = exec_mysql('SELECT SUM(status = 1), SUM(status = 0), SUM(status IS NULL) FROM portals2')[0]
    print get_status(status_before, status_after)
    print 'all done'

if __name__ == '__main__':
    scrape()