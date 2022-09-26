import requests
import geopandas as gpd
from bs4 import BeautifulSoup
import re
import numpy as np
import pandas as pd
import sys
import datetime as dt


def format_doc(x):
    try:
        if len(str(x)) <= 11:
            x = '{:011d}'.format(int(x))
            p1, p2, p3, p4 = int(str(x)[0:3]), int(str(x)[3:6]), int(str(x)[6:9]), int(str(x)[9:])
            return '{0:03d}.{1:03d}.{2:03d}-{3:02d}'.format(p1, p2, p3, p4)
        else:
            x = '{:014d}'.format(int(x))
            p1, p2, p3, p4, p5 = int(str(x)[0:2]), int(str(x)[2:5]), int(str(x)[5:8]), int(str(x)[8:13]), int(str(x)[13:])
            return '{0:02d}.{1:03d}.{2:03d}/{3:04d}.{4:02d}'.format(p1, p2, p3, p4, p5)
    except:
        return None


def create_geometry(x):
    try:
        return Polygon(x)
    except:
        return None


def car_mt(cpf):

    url = 'http://monitoramento.sema.mt.gov.br/apfruralconsulta/index.aspx'

    s = requests.Session()
    headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
               'Accept-Encoding': 'gzip, deflate',
               'Cache-Control': 'max-age=0',
               'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}

    dum = s.get(url, headers=headers)
    cookies = dum.cookies

    soup = BeautifulSoup(dum.content, 'html.parser')
    p1 = soup.find(attrs={'id': '__VIEWSTATE'})['value']
    p2 = soup.find(attrs={'id': '__EVENTVALIDATION'})['value']
    p3 = soup.find(attrs={'id': '__VIEWSTATEGENERATOR'})['value']
    p4 = 0
    p5 = 0

    payload = {'txtCpfCnpjProprietario': cpf,
               '__VIEWSTATE': p1,
               '__EVENTVALIDATION': p2,
               '__VIEWSTATEGENERATOR': p3,
               '__SCROLLPOSITIONX': p4,
               '__SCROLLPOSITIONY': p5,
               'btnBuscar': 'Buscar'}

    soup = BeautifulSoup(s.post(url, data=payload, cookies=cookies, headers=headers).content, 'html.parser')

    a = {x.attrs.get('id').replace('repeater_lab', ''): x.text for x in soup.find_all(
        'span', {'id': re.compile(r'repeater*')}, string=True)}
    n = np.unique([int(re.findall(r'\d+', x)[0]) for x in list(a.keys())])

    f = pd.DataFrame()
    for i in n:
        z = pd.Series(list(a.keys())).loc[pd.Series(list(a.keys())).str.contains(str(i))]
        t = pd.DataFrame([{re.sub(r'_[0-9]', '', j): a.get(j) for j in z.to_list()}])
        f = pd.concat([f, t], ignore_index=True)

    if len(f) > 0:
        return f
    else:
        return None


def cbot_commodity_price(crop=None, year=None, month=None):

    # This code gets the commodities prices in CBOT website
    # Return data in R$ per sc

    if crop is None:
        sys.exit("You must provide a crop. Try 'corn', 'soybeans' or 'oats'.")

    if crop not in ['corn', 'soybeans', 'oats']:
        sys.exit("Crop " + crop + " was not found. Try 'corn', 'soybeans' or 'oats'.")

    s = requests.Session()

    headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
               'Accept-Encoding': 'gzip, deflate, br',
               'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
               'Connection': 'keep-alive',
               'Host': 'www.cmegroup.com',
               'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}

    url = 'https://www.cmegroup.com/CmeWS/mvc/Quotes/Future/{}/G?quoteCodes=null&_=1560171518204'
    productIds = {'dollar': '40', 'soybeans': '320', 'corn': '300', 'oats': '331'}

    quotes = s.get(url.format(productIds.get(crop)), headers=headers).json().get('quotes')
    crop_price = pd.DataFrame(quotes)[['expirationDate', 'priorSettle']]
    crop_price.columns = ['Data', 'Preço']
    crop_price['Data'] = pd.to_datetime(crop_price['Data'], format='%Y%m%d')
    crop_price['Preço'] = crop_price['Preço'].str.replace("'", '.').astype(float)

    currency = s.get(url.format(productIds.get('dollar')), headers=headers).json().get('quotes')
    currency = pd.DataFrame(currency)[['expirationDate', 'priorSettle']]
    currency.columns = ['Data', 'Taxa']
    currency['Data'] = pd.to_datetime(currency['Data'], format='%Y%m%d')
    currency['Taxa'] = 1 / currency['Taxa'].replace('-', None).astype(float)

    crop_price = crop_price.merge(currency, how='inner', on='Data')

    bu2sc = (2.36210 if crop.lower() == 'corn' else 2.20462) if crop.lower() != 'oats' else 4.13365

    crop_price['Preço'] = bu2sc * crop_price['Preço'] * crop_price['Taxa'] / 100

    years = crop_price['Data'].dt.year.to_list()
    months = crop_price['Data'].dt.month.to_list()

    if (year is not None) & (month is not None):
        if (year in years) & (month in months):
            date = np.datetime64(dt.date(year, month, 1))
            crop_price = crop_price.loc[crop_price['Data'] == date]
        else:
            crop_price = None

    if (year is not None) & (month is None):
        if year in years:
            crop_price = crop_price.loc[crop_price['Data'].dt.year == year]
        else:
            crop_price = None

    if (year is None) & (month is not None):
        if month in months:
            crop_price = crop_price.loc[crop_price['Data'].dt.month == month]
        else:
            crop_price = None

    return crop_price
