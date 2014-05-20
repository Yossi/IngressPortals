import sys, os
sys.path.append(os.path.dirname(__file__))

from pprint import pprint, pformat
import json
import dateutil.parser
import datetime
from werkzeug.wrappers import Request, Response
from jinja2 import Environment, FileSystemLoader
from collections import Counter
from util import exec_mysql

def get_timespan(ping, pong=None):
    ping_date = ping
    if pong:
        pong_date = pong
    else:
        pong_date = datetime.datetime.utcnow()

    return (pong_date - ping_date).days

def get_chart_data(cmd='start'):
    data = list(exec_mysql('SELECT ping, pong, `name`, `status` FROM portals2;'))
    first_run = exec_mysql('SELECT min(ping) FROM portals2;')[0][0]

    dataTable = []

    status_name = {True: 'Accepted',
                   False: 'Rejected',
                   None: 'Pending'}

    status_color = {True: '#3366CC',
                    False: '#DC3912',
                    None: '#FF9900'}

    if cmd == 'start' or cmd == None:
        data.sort(key=lambda x: x[0] if x[0] else first_run)
    if cmd == 'end':
        data.sort(key=lambda x: x[1] if x[1] else datetime.datetime.utcnow())
    if cmd == 'days':
        data.sort(key=lambda x: get_timespan(x[0], x[1]))
        data.reverse()

    colors = []
    for row in data:
        if row[3] not in colors:
            colors.append(row[3])
    for i, color in enumerate(colors):
        colors[i] = status_color[color]

    now = datetime.datetime.utcnow()
    for id_, row in enumerate(data):
        ping, pong, name, status = row
        fillings = {'id': status_name[status],
                    'name': name.replace("'", "\\'"),
                    'ping': ping.strftime('%Y, %m-1, %d, %H, %M, %S') if ping else first_run.strftime('%Y, %m-1, %d, %H, %M, %S'),
                    'pong': pong.strftime('%Y, %m-1, %d, %H, %M, %S') if pong else now.strftime('%Y, %m-1, %d, %H, %M, %S')
                   }
        dataTable.append( fillings )

    return {'data': dataTable,
            'colors': colors,
            'count': Counter(zip(*data)[3])}

def render_template(jinja_env, template_name, **context):
    t = jinja_env.get_template(template_name)
    return Response(t.render(context), mimetype='text/html')

def get_json():
    output = []
    for ping, pong, name, status in exec_mysql('SELECT ping, pong, `name`, `status` FROM portals2;'):
        output.append({'ping': ping.strftime('%Y, %m-1, %d, %H, %M, %S') if ping else None,
                       'pong': pong.strftime('%Y, %m-1, %d, %H, %M, %S') if pong else None,
                       'name': name,
                       'status': status})
    return json.dumps(output, indent=4, separators=(',', ': '))

def application(environ, start_response):
    template_path = os.path.join(os.path.dirname(__file__), 'templates')
    jinja_env = Environment(loader=FileSystemLoader(template_path), autoescape=True)

    request = Request(environ)
    cmd = request.args.get('cmd', None)
    if cmd != 'raw':
        response = render_template(jinja_env, 'table.html', **get_chart_data(cmd))
    else:
        response = Response(get_json())

    return response(environ, start_response)

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    #from paste.evalexception.middleware import EvalException
    #application = EvalException(application)
    httpd = make_server('', 80, application)
    print "server running"
    httpd.handle_request()
    print 'exiting'