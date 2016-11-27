from ..urlio import fetch, clear_cache
import json

def _json_from_url(url, refresh=False):
    """
    Fetches a list of JSON formatted object from `url`.
    """
    if refresh:
        clear_cache(url)
    # get the response as text
    response = fetch(url)
    # decode the response
    response = json.loads(response)
    # ensure the response is a list
    if not isinstance(response, list):
        response = [response]
    return response


def fetch_project(host, refresh=False):
    url = '{}/projects'.format(host)
    try:
        return _json_from_url(host, refresh)
    except IOError:
        msg = 'Could not retrieve projects from {}.'.format(host)
        raise IOError(msg)


def fetch_samples(host, projectID, refresh=False):
    url = '{}/projects/{}/samples'.format(host, projectID)
    try:
        return _json_from_url(url, refresh)
    except IOError:
        msg = 'Could not retrieve samples from project {project:} ' \
              'at {host:}.'.format(host=host, project=projectID)
        raise IOError(msg)
