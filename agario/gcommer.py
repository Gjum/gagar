import json
from threading import Thread
import urllib.request
import time
from agario.utils import find_server


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


def gcommer_donate(address, token, *_):
    """
    Donate a token for this server address.
    `address` and `token` should be the return values from find_server().
    """
    token = urllib.request.quote(token)
    url = 'http://at.gcommer.com/donate?server=%s&token=%s' % (address, token)
    response = urllib.request.urlopen(url).read().decode()
    return json.loads(response)['msg']


def gcommer_donate_threaded(interval=5):
    """Run a daemon thread that requests and donates a token every `interval` seconds."""
    def donate_thread():
        while 1:
            gcommer_donate(*find_server())
            time.sleep(interval)

    Thread(target=donate_thread, daemon=True).start()
