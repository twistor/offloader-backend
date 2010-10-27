#!/usr/bin/env python

from unittest import TestCase
import syndicationparser
from filter import Filter
html = """
<html>
2asdfas-fdasfd? <a href="asdf">asdfasfasdf</a>, \n \t ASDFGASFDASDDF asodfisf askjdfjasf asdfkj
</html>
"""


def test_title():
    title = syndicationparser._parse_title(None, html)
    print title
    assert title == "2asdfas-fdasfd? asdfasfasdf ASDFGASFDASDDF", "title parsing failed"

def test_filter():
    mappings = [{'source': 'title'}, {'source': 'description'}, {'source': 'adfasdf'}, {'no source': 'adfasdf'}]
    filter = Filter(mappings)
    result = {}
    result['items'] = [{
        'author': 'Fred',
        'guid': 1234,
        'title': 'Gee golly',
        'description': 'This is fun.'
    }]
    result = filter.filter(result)
    print result
    assert result['items'] == [{'title': 'Gee golly', 'description': 'This is fun.'}]
