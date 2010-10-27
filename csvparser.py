#!/usr/bin/env python

from tablib import Dataset

class FeedsOffloadCSVParser(object):
    def parse(raw):
        data = Dataset()
        data.csv = raw
        print data.json
