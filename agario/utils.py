import json
import urllib.error
import urllib.request

from .client import handshake_version, moz_headers

special_names = 'poland;usa;china;russia;canada;australia;spain;brazil;germany;ukraine;france;sweden;chaplin;north korea;south korea;japan;united kingdom;earth;greece;latvia;lithuania;estonia;finland;norway;cia;maldivas;austria;nigeria;reddit;yaranaika;confederate;9gag;indiana;4chan;italy;bulgaria;tumblr;2ch.hk;hong kong;portugal;jamaica;german empire;mexico;sanik;switzerland;croatia;chile;indonesia;bangladesh;thailand;iran;iraq;peru;moon;botswana;bosnia;netherlands;european union;taiwan;pakistan;hungary;satanist;qing dynasty;matriarchy;patriarchy;feminism;ireland;texas;facepunch;prodota;cambodia;steam;piccolo;ea;india;kc;denmark;quebec;ayy lmao;sealand;bait;tsarist russia;origin;vinesauce;stalin;belgium;luxembourg;stussy;prussia;8ch;argentina;scotland;sir;romania;belarus;wojak;doge;nasa;byzantium;imperial japan;french kingdom;somalia;turkey;mars;pokerface;8;irs;receita federal;facebook;8;nasa;putin;merkel;tsipras;obama;kim jong-un;dilma;hollande' \
    .split(';')


def find_server(region='EU-London', mode=None):
    if mode: region = '%s:%s' % (region, mode)
    opener = urllib.request.build_opener()
    opener.addheaders = moz_headers
    data = '%s\n%s' % (region, handshake_version)
    return opener.open('http://m.agar.io/', data=data.encode()) \
        .read().decode().split('\n')


def get_party_address(party_token):
    opener = urllib.request.build_opener()
    opener.addheaders = moz_headers
    try:
        return opener.open('http://m.agar.io/getToken', data=party_token.encode()) \
            .read().decode().split('\n')
    except urllib.error.HTTPError:
        raise ValueError('Invalid token "%s" (maybe timed out after 10min?)' % party_token)


def gcommer(server=None):
    """
    Try to get a token for this server address.
    `server` has to be ip:port, e.g. `'1.2.3.4:1234'`
    Returns tuple(server, token)
    """
    if not server:
        # no server specified, just get any server
        # this is only useful for testing, as m.agar.io can also be used for this
        url = 'http://at.gcommer.com/status'
        text = urllib.request.urlopen(url).read().decode()
        j = json.loads(text)
        for server, num in j['status'].items():
            if num > 0:
                break  # server is now one of the listed servers with tokens
    url = 'http://at.gcommer.com/claim?server=%s' % server
    text = urllib.request.urlopen(url).read().decode()
    j = json.loads(text)
    token = j['token']
    return server, token
