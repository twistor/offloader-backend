#!/usr/bin/env python

class Filter(object):
    def __init__(self, mappings):
        self.mappings = set([i['source'] for i in mappings if 'source' in i])

    def filter(self, result):
        for item in result['items']:
            for key, value in item.items():
                if key not in self.mappings:
                    del(item[key])
        return result
