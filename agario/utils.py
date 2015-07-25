"""
Copyright (C) 2015  Gjum

code.gjum@gmail.com

This file is part of pyagario.

pyagario is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pyagario is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pyagario.  If not, see <http://www.gnu.org/licenses/>.
"""
import json
import urllib.error
import urllib.request

from .client import handshake_version

special_names = 'poland;usa;china;russia;canada;australia;spain;brazil;germany;ukraine;france;sweden;chaplin;north korea;south korea;japan;united kingdom;earth;greece;latvia;lithuania;estonia;finland;norway;cia;maldivas;austria;nigeria;reddit;yaranaika;confederate;9gag;indiana;4chan;italy;bulgaria;tumblr;2ch.hk;hong kong;portugal;jamaica;german empire;mexico;sanik;switzerland;croatia;chile;indonesia;bangladesh;thailand;iran;iraq;peru;moon;botswana;bosnia;netherlands;european union;taiwan;pakistan;hungary;satanist;qing dynasty;matriarchy;patriarchy;feminism;ireland;texas;facepunch;prodota;cambodia;steam;piccolo;ea;india;kc;denmark;quebec;ayy lmao;sealand;bait;tsarist russia;origin;vinesauce;stalin;belgium;luxembourg;stussy;prussia;8ch;argentina;scotland;sir;romania;belarus;wojak;doge;nasa;byzantium;imperial japan;french kingdom;somalia;turkey;mars;pokerface;8;irs;receita federal;facebook;putin;merkel;tsipras;obama;kim jong-un;dilma;hollande;berlusconi;cameron;clinton;hillary;venezuela;blatter;chavez;cuba;fidel;palin;queen;boris;bush;trump' \
    .split(';')


moz_headers = [
    ('User-Agent', 'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0'),
    ('Origin', 'http://agar.io'),
    ('Referer', 'http://agar.io'),
]


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
