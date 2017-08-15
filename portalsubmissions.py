import json
import datetime
from collections import Counter
from util import exec_mysql, cm
import secret

from flask import Flask, render_template, url_for
app = Flask(__name__)

cm.set_credentials(secret.dbconfig)

def get_timespan(ping, pong=None):
    ping_date = ping
    if pong:
        pong_date = pong
    else:
        pong_date = datetime.datetime.utcnow()

    return (pong_date - ping_date).days

def get_chart_data(cmd='start'):
    data = list(exec_mysql('SELECT ping, pong, `name`, `status`, Id FROM portals2;'))
    first_run = exec_mysql('SELECT min(ping) FROM portals2;')[0][0]

    dataTable = []

    status_name = {True:  'Accepted',
                   False: 'Rejected',
                   None:  'Pending'}

    status_color = {True:  '#3366CC',
                    False: '#DC3912',
                    None:  '#FF9900'}

    if cmd == 'start' or cmd == None:
        pass
        #data.sort(key=lambda x: x[0] if x[0] else first_run)
    if cmd == 'end':
        data.sort(key=lambda x: x[1] if x[1] else datetime.datetime.utcnow())
    if cmd == 'days':
        data.sort(key=lambda x: (get_timespan(x[0], x[1]), x[0]))
        data.reverse()

    colors = []
    for row in data:
        if row[3] not in colors:
            colors.append(row[3])
    for i, color in enumerate(colors):
        colors[i] = status_color[color]

    now = datetime.datetime.utcnow()
    for ping, pong, name, status, id_ in data:
        fillings = {'id': status_name[status],
                    'name': '{} ({} days)'.format(name.replace("'", "\\'"), get_timespan(ping, pong)),
                    'ping': ping.isoformat() if ping else first_run.isoformat(),
                    'pong': pong.isoformat() if pong else now.isoformat()
                   }
        dataTable.append( fillings )

    return {'data': dataTable,
            'colors': colors,
            'count': Counter(zip(*data)[3]),
            'start_url': url_for('start'),
            'end_url': url_for('end'),
            'days_url': url_for('days'),
            'json_url': url_for('get_json'),
            'summary_url': url_for('get_summary_data'),
            'histogram_url': url_for('get_histogram')}

@app.route('/')
@app.route('/start')
def start():
    return render_template('table.html', **get_chart_data(cmd='start'))

@app.route('/end')
def end():
    return render_template('table.html', **get_chart_data(cmd='end'))

@app.route('/days')
def days():
    return render_template('table.html', **get_chart_data(cmd='days'))

@app.route('/json')
def get_json():
    output = []
    for ping, pong, name, status in exec_mysql('SELECT ping, pong, `name`, `status` FROM portals2;'):
        output.append({'ping': ping.isoformat() if ping else None,
                       'pong': pong.isoformat() if pong else None,
                       'name': name,
                       'status': status})
    return json.dumps(output, indent=4, separators=(',', ': '))

@app.route('/summary')
def get_summary_data():
    data = exec_mysql('''SELECT ping, pong, `name`, `status`, image_url, portal_url, notes
                         FROM portals2
                         ORDER BY ping''')
    cols = ['ping', 'pong', 'name', 'status', 'image_url', 'portal_url', 'notes']
    output = []
    for row in data:
        r = dict(zip(cols, row))
        r['days'] = get_timespan(r['ping'], r['pong'])
        r['ping'] = r['ping'].isoformat() if r['ping'] else None
        r['pong'] = r['pong'].isoformat() if r['pong'] else None
        output.append(r)
        
    return render_template('summary.html', **{'data': output})

@app.route('/summary/<date>')
def get_portal_info(date):
    try:
        date = datetime.datetime.utcfromtimestamp(int(date)/1000.0) # attempt to make sure it's date-like (rather than SQLi-like)
        data = exec_mysql('''SELECT ping, pong, `name`, `status`, image_url, portal_url
                             FROM portals2 
                             WHERE ping = '%s';''' % date.strftime("%Y-%m-%d %H:%M:%S"))[0]
        data = dict(zip(['ping', 'pong', 'name', 'status', 'image_url', 'portal_url'], data))
        data['days'] = get_timespan(data['ping'], data['pong'])
        
    except (IndexError, ValueError):
        data = {}

    return render_template('detail.html', data=data)

@app.route('/histogram')
def get_histogram():
    return render_template('histogram.html', **{'data':[(row[0], str(row[0].time())[:2]) for row in exec_mysql('select pong from portals2 where pong is not null')]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
    