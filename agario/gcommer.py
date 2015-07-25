import json
import urllib.request


def gcommer_claim(address=None):
    """
    Try to get a token for this server address.
    `address` has to be ip:port, e.g. `'1.2.3.4:1234'`
    Returns tuple(address, token)
    """
    if not address:
        # get token for any world
        # this is only useful for testing, as m.agar.io can also be used for this
        url = 'http://at.gcommer.com/status'
        text = urllib.request.urlopen(url).read().decode()
        j = json.loads(text)
        for address, num in j['status'].items():
            if num > 0:
                break  # address is now one of the listed servers with tokens
    url = 'http://at.gcommer.com/claim?server=%s' % address
    text = urllib.request.urlopen(url).read().decode()
    j = json.loads(text)
    token = j['token']
    return address, token
