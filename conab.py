import requests
import json
import calendar
import locale
import sys
import pandas as pd
import numpy as np
from historico_safra_ibge import produtividade
import geopandas as gpd


def previsao_safra_conab(uf=None, anosafra=None, cultura=None):

    s = requests.Session()

    safra = str(anosafra - 1) + '/' + str(anosafra - 2000)

    url_ibge = 'https://servicodados.ibge.gov.br/api/v1/localidades/estados'
    regioes = s.get(url_ibge, params={'view': 'nivelado'}).json()
    regioes = {x.get('UF-sigla'): x.get('regiao-nome').upper() for x in regioes}
    regiao = regioes.get(uf.upper())

    payload = {'paramproduto': '[Produto].[' + cultura.upper() + ']',
               'paramsafra': '[Safra].[All Safras]',
               'paramanoAgricola': '[Ano Agricola].[' + safra + ']',
               'paramuf': '[UF].[' + regiao + '].[' + uf.upper() + ']',
               'path': '/home/SIMASA2/EvolucaoEstimativas.cda',
               'dataAccessId': 'ProdutividadeUF'}

    url = 'https://pentahoportaldeinformacoes.conab.gov.br/pentaho/plugin/cda/api/doQuery?'

    res = s.post(url, data=payload, auth=('pentaho', 'password'))

    out = pd.DataFrame(json.loads(res.content).get('resultset'), columns=['Levantamento', 'Rendimento'])

    return out

# previsao_safra_conab(uf='MT', anosafra=2022, cultura='soja')


def calcular_custeio(ano=None, mes=None, safra=0, cultura=None):

    if safra in [0, 1, 2]:
        safra_str = ('1ª SAFRA' if safra == 1 else '2ª SAFRA') if safra != 0 else 'TODAS'
    else:
        sys.exit('Erro: Safra inexistente! Escolha 0 (TODAS), 1 (1ª SAFRA) ou 2 (2ª SAFRA).')

    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

    mon_names = {i: n for i, n in zip(range(1, 13), [x.upper() for x in calendar.month_name[1:13]])}

    payload = {'paramempreendimento': '[Tipo Empreendimento].[AGRICULTURA EMPRESARIAL]',
               'paramproduto': '[Produto].[' + cultura.upper() + ']',
               'paramsafra': '[Tipo Safra].[' + safra_str + ']',
               'paramufMunicipio': '[UF].[UF].[TODAS]',
               'paramano': '[Ano].[' + str(ano) + ']',
               'parammes': '[Mes].[' + mon_names.get(mes) + ']',
               'paramclassificacao': '[Produto Classificacao].[TODAS]',
               'path': '/home/SIAGRO/CustoProducao.cda',
               'dataAccessId': 'SQLCustoTotalPrecoUF'}

    s = requests.Session()

    url = 'https://pentahoportaldeinformacoes.conab.gov.br/pentaho/plugin/cda/api/doQuery?'

    res = s.post(url, data=payload, auth=('pentaho', 'password'))

    out = pd.DataFrame(res.json().get('resultset'), columns=['UF', 'Renda de fatores', 'Custo fixo', 'Custo variável', 'Preço recebido'])

    url_ibge = 'https://servicodados.ibge.gov.br/api/v1/localidades/municipios'
    uf = s.get(url_ibge, params={'view': 'nivelado'}).json()
    uf = np.unique([x.get('UF-sigla') for x in uf])

    yld = produtividade(cultura=cultura.lower(),
                        ano_inicio=2016,
                        ano_fim=2020,
                        safra=safra,
                        nivel=1,
                        local=uf.tolist())

    yld = (yld.mean() / 60).to_dict()

    out['Custo total'] = out.iloc[:, 1:4].sum(axis=1) * [yld.get(x) for x in out['UF']]

    return out


def preco_commodities(ano=None, mes=None, uf=None, cultura=None):

    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

    mon_names = {i: n[0:3] for i, n in zip(range(1, 13), [x.upper() for x in calendar.month_name[1:13]])}

    payload = {'paramproduto': '[Produto].[' + cultura.upper() + ']',
               'paramunidadeComercializacao': '[Unidade Comercializacao].[60 kg]',
               'paramuf': '[UF].[' + uf.upper() + ']',
               'paramdataFinal': '[Ano Mes].[' + '{0:04d}{1:02d}'.format(ano, mes) + '].[' + mon_names.get(mes) + '-' + str(ano) + ']',
               'paramdataInicial': '[Ano Mes].[' + '{0:04d}{1:02d}'.format(ano, mes) + '].[' + mon_names.get(mes) + '-' + str(ano) + ']',
               'paramclassificacao': '[Classificacao].[EM GRÃOS]',
               'path': '/home/SIAGRO/PrecoMedioSerieHistorica.cda',
               'dataAccessId': 'historicoPrecoMedioUf'}

    s = requests.Session()

    cookies = s.get(urlCookies).cookies

    url = 'https://pentahoportaldeinformacoes.conab.gov.br/pentaho/plugin/cda/api/doQuery?'

    res = s.post(url, data=payload, auth=('pentaho', 'password'))

    out = pd.DataFrame(res.json().get('resultset'), columns=['Data', 'Preço'])
    out['Data'] = pd.to_datetime(out['Data'])

    return out.set_index('Data').to_dict()


# df = [pd.DataFrame(preco_commodities(ano=2022, mes=x, cultura='Soja', uf='MT')) for x in np.arange(1, 8, 1)]
# pd.concat(df)
# df = calcular_custeio(ano=2022, mes=5, cultura='Soja')
# df = previsao_safra_conab(uf='MT', safra=2022, cultura='SOJA')


def custo_de_producao(empreendimento='AGRICULTURA EMPRESARIAL', cultura='SOJA', safra='TODAS', tipo_retorno='ha'):

    url = 'https://portaldeinformacoes.conab.gov.br/downloads/arquivos/CustoProducao.txt'

    data = pd.read_csv(url, sep=';')
    dum = (data['empreendimento'].str.strip() == empreendimento.upper()) & (data['produto'].str.strip() == cultura.upper()) & (data['safra'].str.strip() == safra.upper())
    data = data.loc[dum]
    data['ano_mes'] = pd.to_datetime(data['ano_mes'], format='%Y%m')

    data.unidade = data['unidade_comercializacao'].str.strip().unique()[0]
    data.cultura = data['produto'].str.strip().unique()[0]

    data['vlr_custo_total_' + tipo_retorno] = data[list(filter(lambda x: '_' + tipo_retorno in x, data.columns))].sum(axis=1)

    mun = gpd.read_file('/home/victorbenezoli/Aegro/vetores/mun2020').to_crs('EPSG:32722')
    mun['geometry'] = mun['geometry'].centroid
    crop_mun = mun.loc[mun['CD_MUN'].isin(data['cod_ibge'].astype(str).unique())]
    mun['cod_ibge'] = crop_mun.iloc[[np.argmin([x.distance(y) for x in crop_mun.geometry]) for y in mun.geometry], 0].values
    dist = mun[['CD_MUN', 'cod_ibge']].astype('Int64')

    out = data[['ano_mes', 'cod_ibge', 'vlr_custo_total_' + tipo_retorno]]
    out = out.merge(dist, how='outer', on='cod_ibge')
    out = pd.pivot_table(out, values='vlr_custo_total_' + tipo_retorno, columns='CD_MUN', index='ano_mes')
    idx = pd.date_range(np.min(out.index), np.max(out.index), freq='MS')
    out = out.reindex(idx, fill_value=None)
    out = out.interpolate(method='slinear')

    out.unidade = data.unidade
    out.cultura = data.cultura

    return out
