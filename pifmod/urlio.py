from subprocess import check_output
import re

_404_not_found_re = re.compile(r'404 Not Found')

_cache = {}

class DataManagementError(Exception):
    def __init__(self, *args, **kwds):
        Exception.__init__(self, *args, **kwds)
        msg='Please contact bkappes@mines.edu to fix this data ' \
            'availability issue.'
        self.msg = msg

# TODO: Add timestamps to cached values
def fetch(url, cache=True):
    global _cache
    def action():
        response = check_output(['curl', '-s', url])
        if re.search(_404_not_found_re, response):
            raise IOError('Could not locate {}'.format(url))
        return response
    # cached or not cached?
    if cache:
        # if cached, is or is not in _cache?
        if url not in _cache:
            response = action()
            _cache[url] = response
        else:
            respone = _cache[url]
    else:
        response = action()
    return response


def clear_cache(key=None):
    global _cache
    # clear the entire cache
    if key is None:
        _cache = {}
    # clear a specific key/URL
    elif key in _cache:
        del _cache[key]
