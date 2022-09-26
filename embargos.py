import pandas as pd
import json
import requests
from os.path import exists, getmtime
import datetime as dt
from bs4 import BeautifulSoup as bs
import urllib3
import re
import ssl
import OpenSSL
import geopandas as gpd
import sys
import shapefile
from zipfile import is_zipfile, ZipFile
from io import BytesIO
from shapely.geometry import Polygon
import numpy as np

urllib3.disable_warnings()


def to_polygon(x):
    try:
        return Polygon(x)
    except Exception:
        return None


def read_shp_from_zip(data, encoding='utf-8', crs='EPSG:4326'):

    zip_file = ZipFile(BytesIO(data))
    fnames = zip_file.namelist()
    shp = zip_file.open(list(filter(lambda x: '.shp' in x, fnames))[0])
    shx = zip_file.open(list(filter(lambda x: '.shx' in x, fnames))[0])
    dbf = zip_file.open(list(filter(lambda x: '.dbf' in x, fnames))[0])
    prj = zip_file.open(list(filter(lambda x: '.prj' in x, fnames))[0])
    r = shapefile.Reader(shp=shp, shx=shx, dbf=dbf, prj=prj, encoding=encoding)

    df = pd.DataFrame.from_dict([x.get('properties') for x in r.__geo_interface__.get('features')])
    geom = pd.DataFrame.from_dict([x.get('geometry').get('coordinates') for x in r.__geo_interface__.get('features')])[0].values
    df.insert(df.shape[1], 'geometry', geom)
    df['geometry'] = df['geometry'].apply(lambda x: to_polygon(x))
    df.dropna(subset=['geometry'], inplace=True)
    geodf = gpd.GeoDataFrame(df, crs=crs)

    return geodf


def ibama_doc(document):

    if type(document) is not list:
        document = [document]

    s = requests.Session()

    url = 'https://servicos.ibama.gov.br/ctf/publico/areasembargadas/ConsultaPublicaAreasEmbargadas.php'

    headers = {'Accept-Encoding': 'gzip, deflate, br',
               'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
               'Connection': 'keep-alive',
               'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}

    cookies = s.get(url, headers=headers, verify=False).cookies

    out = []
    for doc in document:
        payload = {'formDinAcao': 'atualizar_grid_Areas_Embargadas_ajax',
                   'cpf_cnpj': doc}
        req = requests.post(url, data=payload, verify=False, cookies=cookies)
        if req.status_code == 200:
            try:
                error = bs(req.content, 'html.parser').find(
                    attrs={'id': 'erro'}).get_text()
                out.append(
                    False) if error == 'Não há resultados para essa consulta.' else out.append(None)
            except:
                out.append(True)
        else:
            out.append(None)

    return out


def icmbio_doc(document):

    if type(document) is not list:
        document = [document]

    document = [''.join(filter(str.isdigit, x)) for x in document]

    url = 'https://www.gov.br/icmbio/resolveuid/3e86d613f7954424ab6342dae2b6c1d6'
    req = requests.get(url=url).content
    link = bs(req, 'html.parser').find_all('a', href=re.compile('xlsx'))[0]['href']
    df = pd.read_excel(link)
    out = [df['CPF/CNPJ'].isin([x]).any() for x in document]

    return out


def amazonia_protege_doc(document):

    if type(document) is not list:
        document = [document]

    document = [''.join(filter(str.isdigit, x)) for x in document]

    url = 'http://amazoniaprotege.mpf.mp.br/geo/dadosProdes/buscaCpfCnpj'

    s = requests.Session()

    headers = {'Accept-Encoding': 'gzip, deflate',
               'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
               'Connection': 'keep-alive',
               'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}

    cookies = s.get(url, headers=headers, verify=False).cookies

    out = []
    for doc in document:
        params = {'cpfCnpj': doc}
        res = s.get(url=url, params=params, cookies=cookies).json()
        out.append(len(res) > 0)

    return out


def sema_mt_doc(document):

    if type(document) is not list:
        document = [document]

    url = 'https://geo.sema.mt.gov.br/geoserver/semamt/ows'

    payload = {'service': 'WFS',
               'version': '1.0.0',
               # 'authkey': '541085de-9a2e-454e-bdba-eb3d57a2f492',
               'request': 'GetFeature',
               'typeName': 'semamt:AREAS_EMBARGADAS_SEMA',
               # 'srsname': 'EPSG:100005',
               'outputFormat': 'application/json'}

    s = requests.Session()
    data = s.post(url, data=payload).json()
    feature = gpd.GeoDataFrame(data.get('features'))
    data = pd.DataFrame([x.get('properties') for x in data.get('features')])
    resume = data.replace(' ', None).dropna(subset=['CPF_CNPJ']).groupby(['CPF_CNPJ']).agg({'NOME': 'count', 'AREA': 'sum'}).reset_index()
    out = [resume['CPF_CNPJ'].isin([x]).any() for x in document]

    return out


def semas_pa_doc(document):

    if type(document) is not list:
        document = [document]

    url = 'https://monitoramento.semas.pa.gov.br/ldi/regioesdesmatamento/downloadcsvareasfile'
    df = pd.read_csv(url, encoding='latin-1', sep=';',
                     on_bad_lines='skip', skiprows=2, decimal=',')
    tmp = (df['Proprietário - CPF/CNPJ'].str.split(' - ', expand=True)
           ).iloc[:, 0:2].rename(columns={0: 'Nome', 1: 'CPF_CNPJ'})
    df['Nome'] = tmp['Nome']
    df['CPF_CNPJ'] = tmp['CPF_CNPJ']
    out = [df['CPF_CNPJ'].isin([x]).any() for x in document]

    return out


def ibama_geospatial(save=False, outfile=None, to_sql=False, engine=None):

    s = requests.Session()

    payload = {'service': 'WFS',
               'version': '2.0.0',
               'request': 'GetFeature',
               'typeName': 'publica:vw_brasil_adm_embargo_a',
               'outputFormat': 'application/json'}

    url = 'http://siscom.ibama.gov.br/geoserver/publica/ows'
    df = s.post(url, payload)

    if df.ok:
        out = gpd.GeoDataFrame().from_features(df.json())
        out.columns
        out = out[['nom_pessoa', 'cpf_cnpj_infrator', 'nom_municipio', 'sig_uf', 'geometry']]
        out.set_crs('EPSG:4326', inplace=True)
        out.columns = ['nome', 'documento', 'municipio', 'uf', 'geometry']
        # out.insert(4, 'area', out.to_crs('EPSG:32722').area / 1e4)
        # emb_ibama['data_tad'] = pd.to_datetime(emb_ibama['data_tad'].str.replace('Z',''))
        # emb_ibama['data_geom'] = pd.to_datetime(emb_ibama['data_geom'].str.replace('Z',''))
        if save:
            if outfile is None:
                sys.exit('Error: You must provide a path to save the file. Set the "outfile" argument.')
            out.to_file(outfile)
        if to_sql:
            if engine is None:
                sys.exit('Error: You must provide an engine when save the data in SQL server.')
            out.to_postgis(name='embargos_ibama', con=engine, if_exists='replace', schema='public')
        return out
    else:
        print('Error: The website is down. Try again later.')
        return -1


def icmbio_geospatial(save=False, outfile=None, to_sql=False, engine=None):

    url = 'https://www.gov.br/icmbio/resolveuid/3e86d613f7954424ab6342dae2b6c1d6'
    req = requests.get(url=url)
    if req.ok:
        link = bs(req.content, 'html.parser')
        link = link.find_all('a', href=re.compile('shp'))[0]['href']
        out = gpd.read_file(link, crs='EPSG:4326')
        out = out[['autuado', 'cpf_cnpj', 'municipio', 'uf', 'nome_uc', 'geometry']]
        out.columns = ['nome', 'documento', 'municipio', 'uf', 'nome_da_uc', 'geometry']
        # out.insert(5, 'area', out.to_crs('EPSG:32722').area / 1e4)
        out.to_crs('EPSG:4326', inplace=True)

        if save:
            if outfile is None:
                sys.exit('Error: You must provide a path to save the file. Set the "outfile" argument.')
            out.to_file(outfile)

        if to_sql:
            if engine is None:
                sys.exit('Error: You must provide an engine when save the data in SQL server.')
            out.to_postgis(name='embargos_icmbio', con=engine, if_exists='replace', schema='public')

        return out
    else:
        print('Error: The website is down. Try again later.')
        return -1


def ldi_pa_geoespacial(save=False, outpath=None, type='all'):

    if type not in ['automatizado', 'manual', 'all']:
        print('Erro! O tipo retornado deve ser "automatizado", "manual" ou "all".')
        sys.exit()

    url = 'https://monitoramento.semas.pa.gov.br/ldi/regioesdesmatamento/baixartodosshapefile'

    s = requests.Session()

    auto = s.get(url, params={'tipoShape': 'AUTOMATIZADO'})
    manual = s.get(url, params={'tipoShape': 'MANUAL'})

    auto_df = read_shp_from_zip(data=auto.content, encoding='latin1').replace('', None)
    manual_df = read_shp_from_zip(data=manual.content, encoding='latin1').replace('', None)

    if type.lower() == 'automatizado':
        if save:
            open(outpath + 'ldi_automatizado.zip', 'wb').write(auto.content)
        else:
            return auto_df
    elif type.lower() == 'manual':
        if save:
            open(outpath + 'ldi_manual.zip', 'wb').write(manual.content)
        else:
            return manual_df
    else:
        if save:
            open(outpath + 'ldi_automatizado.zip', 'wb').write(auto.content)
            open(outpath + 'ldi_manual.zip', 'wb').write(manual.content)
        else:
            auto_df['tipo'] = 'automatizado'
            manual_df['tipo'] = 'manual'
            return pd.concat([auto_df, manual_df], ignore_index=True)


# from sqlalchemy import create_engine
#
# usr = 'victor'
# psw = '178398392'
# adr = 'localhost'
# loc = 'dados'
#
# engine = create_engine('postgresql://{0}:{1}@{2}:5432/{3}'.format(usr, psw, adr, loc))
#
# _ = icmbio_geospatial(to_sql=True, engine=engine)
# _ = ibama_geospatial(to_sql=True, engine=engine)

# _ = icmbio_geospatial(save=True, outfile='/home/victorbenezoli/Aegro/Análise socioambiental/icmbio_embargos.gpkg')
# _ = ibama_geospatial(save=True, outfile='/home/victorbenezoli/Aegro/Análise socioambiental/ibama_embargos.gpkg')
# ibama_geospatial('/home/victorbenezoli/Aegro/Análise socioambiental/ibama_embargos.gpkg')
# def SEMAS_PA(document):
#
#     if type(document) is not list:
#         document = [document]
#
#     headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
#                'Accept-Encoding': 'gzip, deflate, br',
#                'Connection': 'keep-alive',
#                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
#                'X-Requested-With': 'XMLHttpRequest'}
#
#     url = 'https://monitoramento.semas.pa.gov.br/ldi/consultaMapa/mapa'
#     s = requests.Session()
#     cookies = s.get(url, headers=headers).cookies
#
#     url = 'https://monitoramento.semas.pa.gov.br/ldi/consultaMapa/imoveis/PROPRIETARIO_POSSUIDOR/count'
#
#     out = []
#     for doc in document:
#         payload = {'filtro': doc, 'pagina': '1'}
#         out.append(int(s.get(url, params=payload, headers=headers).text) > 0)
#
#     return out
