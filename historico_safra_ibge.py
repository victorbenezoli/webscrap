import pandas as pd
import numpy as np
import json
import requests
import difflib
import sys
from fuzzywuzzy import fuzz
from urllib.parse import unquote
# crop, start_year, end_year, nivel, local = 'Milho', 2011, 2020, 2, ['3522406']

# requests.get('https://apisidra.ibge.gov.br/values/t/839/n6/all/v/112/p/all/c81/31693,114254').text

# requests.get(url='https://servicodados.ibge.gov.br/api/v3/agregados/839/periodos/2010|2011/variaveis/112?localidades=N6[3522406]&classificacao=112[31693]').text

def historico_safra_ibge(crop=None, start_year=None, end_year=None, nivel=1, local=None):

    if start_year > end_year:
        exit('O ano inicial deve ser menor que o ano final.')

    if type(local) is not list:
        local = [local]

    if nivel == 1:
        local = [x.upper() for x in local]
        ufCodeId = [{'id': x.get('UF-id'), 'sigla': x.get('UF-sigla')} for x in requests.get('https://servicodados.ibge.gov.br/api/v1/localidades/estados?view=nivelado').json()]
        local = [x.get('id') for x in ufCodeId if x.get('sigla') in local]
    else:
        dummy = []
        for x in local:
            base = 'https://servicodados.ibge.gov.br/api/v1/localidades/municipios/'
            if len(requests.get(base + str(x)).json()) > 0:
                dummy.append(x)
            else:
                print('O código do município ' + str(x) + ' não existe!')
        local = dummy

    if nivel == 1:
        nivel = 'N3'
    elif nivel == 2:
        nivel = 'N6'
    else:
        exit('Escolha o nível 1: Estadual ou 2: Municipal.')

    reqCropId = requests.get(url='https://servicodados.ibge.gov.br/api/v3/agregados/1612/metadados?view=nivelado')

    tab = reqCropId.json().get('classificacoes')[0].get('categorias')[1:]

    cropIds = pd.DataFrame({'id':   [x['id']   for x in tab], 'nome': [x['nome'] for x in tab]})

    cropNameId = cropIds.loc[[crop.lower() in x.lower() for x in cropIds['nome'].tolist()], 'nome']

    periodo = '|'.join([str(x) for x in np.arange(start_year,end_year,1)])

    local_str = ','.join([str(x) for x in local])

    if len(cropNameId) > 0:

        cropId = cropIds.loc[cropIds['nome'].isin(cropNameId),'id'].values[0]

        tmp = requests.get(url='https://servicodados.ibge.gov.br/api/v3/agregados/1612/periodos/' + periodo +
                               '/variaveis/112?localidades=' + nivel + '[' + local_str + ']&classificacao=81[' + str(cropId) + ']')

        nm = pd.DataFrame.from_dict([x.get('localidade').get('id') for x in json.loads(tmp.content)[0].get('resultados')[0].get('series')])
        df = pd.DataFrame.from_dict([x.get('serie') for x in json.loads(tmp.content)[0].get('resultados')[0].get('series')]).T

        df.columns = nm[0].tolist()
        df = df.replace(['-','...'],None).astype(float)

    else:
        df = pd.DataFrame({'yield': [None] * (end_year - start_year + 1)})

    return df


def produtividade(cultura=None, safra=None, ano_inicio=None, ano_fim=None, nivel=1, local=None):

    if ('milho' in cultura.lower()):
        if safra is None:
            sys.exit('Erro: Você precisa escolher a safra. Escolha 0 (total), 1 (1ª safra) ou 2 (2ª safra).')
        if safra not in [0, 1, 2]:
            sys.exit('Erro: Opção inválida para safra de milho. Escolha 0 (total), 1 (1ª safra) ou 2 (2ª safra).')

    s = requests.Session()

    cls = '81' if 'milho' in cultura.lower() else '782'
    tab = '839' if 'milho' in cultura.lower() else '5457'

    if ano_inicio > ano_fim: sys.exit('Ano inicial deve ser menor que o final.')

    local = [local] if type(local) != list else local

    if nivel == 1:
        url = 'https://servicodados.ibge.gov.br/api/v1/localidades/estados?view=nivelado'
        ufcode = {x.get('UF-sigla'): x.get('UF-id') for x in s.get(url).json()}
        local = [str(ufcode.get(x.upper())) for x in local]

    nivel = ('N6' if nivel == 2 else 'N3') if nivel <= 2 else sys.exit('O nível deve ser igual a 1 para estadual ou 2 para municipal.')

    if 'milho' not in cultura.lower():
        url = 'https://servicodados.ibge.gov.br/api/v3/agregados/5457/metadados?view=nivelado'
        cropIdTable = pd.DataFrame(s.get(url).json().get('classificacoes')[0].get('categorias'))
        cropId = [fuzz.partial_ratio(x.lower(), cultura.lower()) for x in cropIdTable['nome']]
        sys.exit('A cultura não existe no banco de dados do IBGE.') if not any(np.array(cropId) > 75) else ''
        cultura = str(cropIdTable.iloc[np.argmax(cropId), 0])
    else:
        cultura = '31693' if safra == 0 else '114253' if safra == 1 else '114254'

    periodo = '|'.join([str(x) for x in np.arange(ano_inicio,ano_fim+1,1)])
    localList = ','.join(local)

    params = {'localidades': nivel + '[' + localList + ']', 'classificacao': cls + '[' +  cultura + ']'}

    url = 'https://servicodados.ibge.gov.br/api/v3/agregados/' + tab + '/periodos/' + periodo + '/variaveis/112'
    url = s.get(url, params=params).url
    url = unquote(url)

    df = s.get(url).json()[0]
    df = pd.DataFrame([x.get('serie') for x in df.get('resultados')[0].get('series')]).T
    df.columns = local if nivel == 'N6' else [list(ufcode.keys())[int(list(ufcode.values()).index(int(x)))] for x in local]
    df = df.replace(['-', '...', '..'], None).astype(float)

    return df
