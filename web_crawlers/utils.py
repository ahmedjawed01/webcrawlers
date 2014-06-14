#! /usr/bin/python
#! -*- coding: utf-8 -*-
import re
import hashlib
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from datetime import date, timedelta, datetime
import requests_cache
import json
import urllib
import urllib2
import urlparse
import os

number_pattern = re.compile(r'''\d+''',re.IGNORECASE)
pets_pattern = re.compile(ur'''(\b[^\.;\n\r\t]*(\bkat\b|\bhund\b|\bhusdyr\b).*?)[\.;\n\r\t\xa0]''',re.IGNORECASE)
zip_pattern = re.compile('[0-9]{4}')
cacher = requests_cache.CachedSession(cache_name='geocode',backend='redis',expire_after=60*60*24*2,min_cache_response_size=200)
cacher_long = requests_cache.CachedSession(cache_name='cacher_long',backend='redis',expire_after=60*60*24*14,min_cache_response_size=200)

def type_from_desc(desc):
    desc = desc.replace('/',' ') #rækkehus/hus -> rækkehus hus
    house_words = ['dobbelthus','klyngehus', u'gårdhus', u'rækkehus', u'fritlæggende hus', 'familiehus', 'villa']
    if any(word in desc.lower() for word in house_words): return 'House'
    return 'Apartment'

def uNorm(txt):
    return txt.replace(u'\xf8','o').replace(u'\xe6','e').replace(u'\xe5','a').replace(u'\xd8','O')

def parse_zip(inp):
    return int(zip_pattern.findall(inp)[0])

def parse_desc(d):
    return '\n'.join([x.strip() for x in d if x.strip()])

def parse_price(price):
    return int(number_pattern.findall(price.strip().replace('.',''))[0])

def parse_price_n(price):
    try:
        return int(number_pattern.findall(price.strip().replace('.',''))[0])
    except:
        return 0

def parse_address(addrtext):
    firstnum = number_pattern.findall(addrtext)
    house_numb = int(firstnum[0])
    street_name = addrtext[:addrtext.find(firstnum[0])].strip()
    return {'street':street_name, 'house_number': house_numb}

def parse_date(datetxt):
    if not type(datetxt) is list: datetxt = [datetxt]
    try:
        MONTHS = {"":0, "jan":1, "feb":2, "mar":3, "apr":4, "maj":5, "jun":6, "jul":7, "aug":8, "sep":9, "okt":10, "nov":11, "dec":12}
        available_txts = ['snarest', 'nu', 'd.d.', 'now', 'klar til indflytning', 'snarest', 'ledig nu']
        datetxt = strip_lower_ar(datetxt)
        if re.findall('[0-9]{10,12}',str(datetxt[0])):
            return str(date.fromtimestamp(float(datetxt[0])))    
        if datetxt[0] in available_txts or ' '.join(datetxt) in available_txts:
            return str(date.today())
        if re.search('[a-z]+',datetxt[1]):
            datetxt[1] = MONTHS[datetxt[1][0:3]]
        datetemp = map(int, datetxt)
        if len(str(datetemp[2])) == 2: #short year format like 13 instead of 2013, add 20
            datetemp[2] = int('20'+str(datetemp[2]))      
        return str(date(datetemp[2], datetemp[1], datetemp[0]))
    except:
        return None

def strip_lower_ar(ar):
    return [re.sub('[^0-9a-zA-Z]','',x.strip().lower()) for x in ar]

def hashtxt(inp):
    md5 = hashlib.md5()
    md5.update(inp.encode('utf-8'))
    return md5.hexdigest()

def parse_imglist(responseurl,imgs,encode=False):
    if not encode: return [urljoin_rfc(responseurl,a.strip()) for a in imgs if a]
    if encode: return ['ENCODED:'+urljoin_rfc(responseurl,a.strip()) for a in imgs if a]

def zip_from_city(c):
    basepath = os.path.dirname(__file__)
    j = json.loads(open(basepath+'/cities.json','rb').read())
    return j[c.lower().strip()]

def get_zip(street,city):
    res = json.loads(cacher_long.get('http://maps.googleapis.com/maps/api/geocode/json?address=' + urllib2.quote(street.strip().encode('utf-8')) + '+' + urllib2.quote(city.strip().encode('utf-8')) + ',denmark&sensor=false', timeout=10).text)
    try:
        return int(res['results'][0]['address_components'][-1]['long_name'])
    except Exception:
        geo = res['results'][0]['geometry']['location']
        rev = reverse_geocode([geo['lat'],geo['lng']])
        return rev['zip_code']
    
def reverse_geocode(coords):
        decode_url = 'http://maps.googleapis.com/maps/api/geocode/json?latlng='+str(coords[0])+','+str(coords[1])+'&sensor=false'
        res = json.loads(cacher_long.get(decode_url).text)
        try:
            house_number = number_pattern.findall([r['long_name'] for r in res['results'][0]['address_components'] if 'street_number' in r['types']][0].split("-")[0])[0]
        except Exception:
            house_number = None
        street_name = [r['long_name'] for r in res['results'][0]['address_components'] if 'route' in r['types']][0]
        zip_code = [r['long_name'] for r in res['results'][0]['address_components'] if 'postal_code' in r['types']][0]
        return {'house_number':house_number,'street_name':street_name,'zip_code':zip_code}

def cache_get(url):
    return cacher.get(url).text

def get_domains(url):
    domain = urlparse.urlparse(url).netloc.replace('www.','')
    return "http://www.{0}, www.{0}, {0}".format(domain).split(', ')

def encode_url(url):
    url = url.strip().encode('utf-8')
    url = url.replace('ENCODED:','')
    p = urlparse.urlsplit(urllib2.unquote(url))
    query = urlparse.parse_qsl(p.query)
    p2 = p._replace(query=urllib.urlencode(query))
    p2 = p2._replace(path=urllib2.quote(p2.path))
    print "ENCODED:{0}".format(urlparse.urlunsplit(p2))
    return "ENCODED:{0}".format(urlparse.urlunsplit(p2))

def get_rental_period_id(years):
    unlimited = 1
    over_12_months = 2
    under_12_months = 3
    if not years: return None
    if years == 'unlimited': return unlimited
    if years < 1: return under_12_months
    if years >= 1: return over_12_months
    
def get_rental_period_id_boligportal(id):
    unlimited = 1
    over_12_months = 2
    under_12_months = 3
    if int(id) == 1: return under_12_months
    if int(id) == 2 or int(id) == 4: return over_12_months
    if int(id) == 1: return unlimited
    raise Exception('not valid id')
    
def parse_url(base,url):
    if 'http' in url: return url
    return base+'/'+url






