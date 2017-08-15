#!/usr/bin/python

# apt-get install python-dev libmysqlclient-dev

#####
def smart_dir(o):
    from pprint import pprint
    return type(o), [x for x in dir(o) if not x.startswith('_')]
#####

import argparse
import base64
import datetime
import operator
from itertools import chain
from urlparse import urlsplit, urlunsplit, parse_qs

import httplib2
from dateutil.parser import parse

# https://developers.google.com/gmail/api/quickstart/quickstart-python
from apiclient import errors
from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow, argparser

import secret
from util import exec_mysql, cm

# https://developers.google.com/gmail/api/v1/reference/


cm.set_credentials(secret.dbconfig)


# Path to the client_secret.json file downloaded from the Developer Console
CLIENT_SECRET_FILE = 'client_secret.json'

# Check https://developers.google.com/gmail/api/auth/scopes
# for all available scopes
OAUTH_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'

# Location of the credentials storage file
STORAGE = Storage('gmail.storage')

def ListMessagesMatchingQuery(service, user_id, query=''):
    """List all Messages of the user's mailbox matching the query.

    Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    query: String used to filter messages returned.
    Eg.- 'from:user@some_domain.com' for Messages from a particular sender.

    Returns:
    List of Messages that match the criteria of the query. Note that the
    returned list contains Message IDs, you must use get with the
    appropriate ID to get the details of a Message.
    """
    try:
        response = service.users().messages().list(userId=user_id, q=query).execute()
        messages = []
        if 'messages' in response:
            messages.extend(response['messages'])
        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId=user_id, q=query, pageToken=page_token).execute()
            messages.extend(response['messages'])
        return messages
    except errors.HttpError, error:
        print 'An error occurred: %s' % error

def get_start_date():
    dates = list(exec_mysql('SELECT max(ping), max(pong) FROM portals2;')[0])
    dates.append(datetime.datetime(2013, 11, 15))  # closed beta begin date
    #dates.append(datetime.datetime(2015, 5, 12))  # debuging date
    #return dates[-1].date()
    dates = filter(lambda x: bool(x), dates)
    if len(dates) > 1:
        return max(dates).date() - datetime.timedelta(days=1)
    else:
        return dates[0].date() - datetime.timedelta(days=1)

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
    return '"' + urlunsplit(newparts) + '"'

def get_service():
    # Parse the command-line arguments (e.g. --noauth_local_webserver)
    parser = argparse.ArgumentParser(parents=[argparser])
    flags = parser.parse_args()

    # Start the OAuth flow to retrieve credentials
    flow = flow_from_clientsecrets(CLIENT_SECRET_FILE, scope=OAUTH_SCOPE)
    http = httplib2.Http()

    # Try to retrieve credentials from storage or run the flow to generate them
    credentials = STORAGE.get()
    if credentials is None or credentials.invalid:
      credentials = run_flow(flow, STORAGE, flags, http=http)

    # Authorize the httplib2.Http object with our credentials
    http = credentials.authorize(http)

    # Build the Gmail service from discovery
    service = build('gmail', 'v1', http=http)
    return service

def scrape(service):
    pings = ('Ingress Portal Submitted',
             'Portal submission confirmation',)
    pongs = ('Ingress Portal Live',
             'Ingress Portal Rejected',
             'Ingress Portal Duplicate',
             'Ingress Portal Game Rejected',
             'Portal review complete',)

    print 'Hello', service.users().getProfile(userId='me').execute()['emailAddress']

    query = ('(from:ingress-support@google.com OR from:super-ops@google.com OR ingress-support@nianticlabs.com)'
             ' after:%(date)s subject:"Portal"' % {'date': get_start_date()})
    # print query

    user_id = 'me'
    emails = ListMessagesMatchingQuery(service, user_id, query=query)[::-1]

    if len(emails): print 'emails found. proccessing...'
    else: print 'no new emails found'

    status_before = exec_mysql('SELECT SUM(status = 1), SUM(status = 0), SUM(status IS NULL) FROM portals2')[0]

    for m in emails:
        message = service.users().messages().get(userId=user_id, id=m['id'], format='full').execute()
        for header in message['payload']['headers']:
            if header['name'] == 'Date':
                 date = header['value']
                 date = parse(date, ignoretz=True)
            if header['name'] == 'Subject':
                subject = header['value']
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/html':
                        html = base64.b64decode(part['body']['data'].replace('-', '+').replace('_', '/'))
        ##########################
        #print date, subject, html

        if ':' in subject:
            preamble, portal_name = subject.partition(':')[::2]
            portal_name = portal_name.lower().strip()

            status = ('Live' in preamble or "we've accepted your submission" in html)

            image_url = html.partition('src="')[2].partition('" alt="')[0]

            portal_url = html.partition('<a href="')[2].partition('">')[0].replace('&amp;', '&')
            portal_url = canonicalize_url(portal_url) if 'll' in portal_url else 'null'

            #print preamble, portal_name, status, image_url, portal_url

            if preamble in pings and date not in set(chain(*exec_mysql('SELECT ping FROM portals2'))):
                print subject
                print 'new submitted portal'
                exec_mysql("""INSERT INTO portals2 (ping, `name`, image_url) VALUES ('%s', "%s", '%s') ON DUPLICATE KEY UPDATE image_url='%s';""" % (date, portal_name.replace('"', '\\"'), image_url, image_url))
                #print """INSERT INTO portals2 (ping, `name`, image_url) VALUES ('%s', "%s", '%s') ON DUPLICATE KEY UPDATE image_url='%s';""" % (date, portal_name.replace('"', '\\"'), image_url, image_url)

            if preamble in pongs and date not in set(chain(*exec_mysql('SELECT pong FROM portals2'))):
                print subject
                print 'portal response received'
                names = list(chain(*exec_mysql('SELECT `name` FROM portals2 WHERE status is null;')))
                if names.count(portal_name) == 1:
                    exec_mysql("""UPDATE portals2 SET pong = '%s', `status` = %s, portal_url = %s WHERE `name` = "%s" AND status is null LIMIT 1;""" % (date, status, portal_url, portal_name.replace('"', '\\"')))
                    #print """UPDATE portals2 SET pong = '%s', `status` = %s, portal_url = %s WHERE `name` = "%s" AND status is null LIMIT 1;""" % (date, status, portal_url, portal_name.replace('"', '\\"'))
                else:
                    # id = exec_sql("""SELECT Id FROM portals2 WHERE image_url = '%s';""" % image_url)[0]
                    if image_url:
                        print 'attempting image_url match'
                        exec_mysql("""UPDATE portals2 SET pong = '%s', `status` = %s, portal_url = %s WHERE image_url = '%s' AND status is null LIMIT 1;""" % (date, status, portal_url, image_url))
                        #print """UPDATE portals2 SET pong = '%s', `status` = %s, portal_url = %s WHERE image_url = '%s' AND status is null LIMIT 1;""" % (date, status, portal_url, image_url)
                    else:
                        print 'FAILED! duplicate or modified name; attention required'
                        exec_mysql("""INSERT INTO portals2 (pong, `name`, `status`, portal_url) VALUES ('%s', "%s", %s, %s) ON DUPLICATE KEY UPDATE Id=Id;""" % (date, portal_name.replace('"', '\\"'), status, portal_url))
                        #print """INSERT INTO portals2 (pong, `name`, `status`, portal_url) VALUES ('%s', "%s", %s, %s) ON DUPLICATE KEY UPDATE Id=Id;""" % (date, portal_name.replace('"', '\\"'), status, portal_url)

    status_after = exec_mysql('SELECT SUM(status = 1), SUM(status = 0), SUM(status IS NULL) FROM portals2')[0]
    print get_status(status_before, status_after)
    print 'all done'


if __name__ == '__main__':
    service = get_service()
    scrape(service)
