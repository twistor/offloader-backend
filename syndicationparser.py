#!/usr/bin/env python

import feedparser
from time import mktime
from lxml import html
import re

regex = re.compile(r'[\s,]+')

class FeedsOffloadSyndicationParser(object):
    def parse(self, raw):
        d = feedparser.parse(raw)
        result = {}
        result['items'] = []
        result['description'] = d.feed.get('description', '')
        result['title'] = d.feed.get('title', '')
        result['title'] = _parse_title(result['title'], result['description'])
        result['link'] = d.feed.get('link', '').strip()
        print len(d['entries'])
        for entry in d.entries:
            i = {}
            i['description'] = entry.get('description', '')
            i['title'] = entry.get('title', '')
            i['title'] = _parse_title(i['title'], i['description'])
            i['url'] = entry.get('link', '').strip()
            i['guid'] = entry.get('id', i['url']).strip()
            # Todo: look for author in source
            i['author_name'] = ''
            author = entry.get('author_detail', None) or d.get('author_detail', None)
            if author:
                i['author_name'] = author.get('name', '')
            i['timestamp'] = int(mktime(entry.get('updated_parsed', None)))
            i['tags'] = []
            i['domains'] = {}

            for term in i['tags']:
                if term['domain'] not in i['domains']:
                    i['domains'][term['domain']] = []
                i['domains'][term['domain']].append(len(i['tags']) - 1)
                i['tags'].append(term['term'])

            result['items'].append(i)
        return len(result['items']), result

def _parse_title(title, body):
    if not title and body:
        body = html.document_fromstring(body).text_content().strip()
        title = regex.split(body, 3)[:3]
        title = ' '.join(title)
    return title
