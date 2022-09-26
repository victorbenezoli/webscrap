import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import geopandas as gpd
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

s = requests.Session()

url = 'https://servicodados.ibge.gov.br/api/v1/localidades/estados'
uf = s.get(url, params = {'view': 'nivelado'}).json()
uf = [x.get('UF-sigla').lower() for x in uf]

url = 'http://acervofundiario.incra.gov.br/i3geo/ogc.php'

payload = [{'tema': 'certificada_sigef_particular_{}'.format(x),
            'version': '2.0.0',
            'srsname': 'EPSG:4326',
            'typename': 'ms:certificada_sigef_particular_{}'.format(x),
            'service': 'WFS',
            'request': 'GetFeature',
            'outputFormat': 'GML3'} for x in uf]

out = gpd.read_file(s.get(url, params=payload[0], verify=False).url)

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
           'Accept-Encoding': 'gzip, deflate, br',
           'Host': 'sigef.incra.gov.br',
           'sec-ch-ua': '"Google Chrome";v="105", "Not)A;Brand";v="8", "Chromium";v="105"'}

BeautifulSoup(s.get('https://sigef.incra.gov.br/geo/parcela/detalhe/714be5ee-e0cb-494c-8f6a-5deb39975179/', verify=False, headers=headers).text)
