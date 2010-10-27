#!/usr/bin/env python

import eventlet
from eventlet import GreenPool, import_patched, spawn, spawn_n, sleep, wsgi
from eventlet.green import urllib2
pymongo = import_patched('pymongo')
from pymongo.errors import AutoReconnect
syndicationparser = import_patched('syndicationparser')
from syndicationparser import FeedsOffloadSyndicationParser
from csvparser import FeedsOffloadCSVParser
from filter import Filter
from uuid import uuid1
from json import dumps, loads
import os, sys
from httplib import responses as HTTPResponses

parsers = set(('FeedsOffloadSyndicationParser', 'FeedsOffloadCSVParser'))

sender_id = "82209006-86FF-4982-B5EA-D1E29E55D481"
firefox_user_agent = "Mozilla/5.0 (X11; Linux i686 on x86_64; rv:2.0.1) Gecko/20100101 Firefox/4.0.1"
BAD_REQUEST_LIMIT = 10

#initialize

try:
    db = pymongo.Connection()
except pymongo.errors.AutoReconnect:
    sys.exit("Database is down.")
hosts = db.offload.hosts
hosts.drop()
completed_jobs = db.offload.completed_jobs
completed_jobs.drop()
etags = db.offload.etags
etags.drop()
g_pool = GreenPool()

# code

def save_job(**kwargs):
    #print "Saving job:", kwargs
    completed_jobs.save(kwargs)

def worker(id, msg, host):
    url = msg['source'].strip()
    print "looking up etag for", url
    print host
    headers = {'User-Agent': firefox_user_agent}

    if url in host:
        if "etag" in host[url]:
            headers['If-None-Match'] = host[url]['etag']
        if "last-modified" in host[url]:
            headers['If-Modified-Since'] = host[url]['last-modified']

    req = urllib2.Request(url, None, headers)

    print "starting download"

    try:
        res = urllib2.urlopen(req)
        print "completed download"

    except urllib2.HTTPError as e:
        print HTTPResponses[e.code]
        save_job(_id=id, code=e.code)
        return

    except urllib2.URLError as e:
        if e.reason[0][0] == -3:
            print "request timed out"
            error = {'code': e.reason[0][0], 'msg': e.reason[0][1]}
            save_job(_id=id, error=error, code=500)
            return

    if 'parser' in msg and 'plugin_key' in msg['parser'] and msg['parser']['plugin_key'] in parsers:
        parser = globals()[msg['parser']['plugin_key']]()
        count, result = parser.parse(res.read())
        filter = Filter(msg['processor']['config']['mappings'])
        save_job(_id=id, count=count, result=filter.filter(result), code=200)

    host[url] = dict(res.info())
    print hosts.save(host)

def find_job(msg):
    job = completed_jobs.find_one({'_id': msg['id']})
    if job:
        completed_jobs.remove({'_id': msg['id']})
        return job
    return {'code': 201}

def add_job(env, start_response, host):
    msg = env['wsgi.input'].read()
    try:
        msg = loads(msg)
    except ValueError:
        return bad_request(env, start_response, host)
    id = str(uuid1())
    g_pool.spawn(worker, id, msg, host)
    start_response('200 OK', [('Content-Type', 'application/json')])
    return [dumps(id)]

def check_job(env, start_response, host):
    msg = env['wsgi.input'].read()
    try:
        msg = loads(msg)
    except ValueError:
        return bad_request(env, start_response, host)
    job = find_job(msg)
    response_code = ' '.join([str(job['code']), HTTPResponses[job['code']]])

    if job['code'] == 200:
        del(job['code'])
        start_response(response_code , [('Content-Type', 'application/json')])
        return [dumps(job)]
    else:
        start_response(response_code , [])
        return []

def get_host(ip):
    host = hosts.find_one({'_id': ip})
    if not host:
        host = {'_id': ip, 'bad_requests': 0}
        hosts.save(host)
    return host

def bad_host(host):
    print "Bad host:", host
    hosts.update({'_id': host['_id']}, {'$inc' : { 'bad_requests': 1 }})

def bad_request(env, start_response, host):
    bad_host(host)
    start_response('405 Method Not Allowed', [])
    return []

def request_handler(env, start_response):
    try:
        host = get_host(env['REMOTE_ADDR'])

        if host['bad_requests'] >= BAD_REQUEST_LIMIT:
            start_response('403 Forbidden', [])
            return []

        if env['REQUEST_METHOD'] != 'POST':
            bad_host(host)
            start_response('405 Method Not Allowed', [])
            return []

        if env['PATH_INFO'] == '/job/add':
            return add_job(env, start_response, host)

        if env['PATH_INFO'] == '/job/check':
            return check_job(env, start_response, host)

        bad_request(host)
        start_response('403 Forbidden', [])
        return []

    except AutoReconnect:
        start_response('500 Internal Server Error', [])
        return []




if __name__ == "__main__":
    wsgi.server(eventlet.listen(('', 8080)),
        request_handler,
        keepalive=False,
        max_size=1000,
        max_http_version='HTTP/1.0'
    )
