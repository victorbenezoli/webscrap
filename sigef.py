from requests import Session
from bs4 import BeautifulSoup as bs
import urllib3
import numpy as np
import pandas as pd
from io import BytesIO
from document import check_document
from resolve_captcha import resolve_captcha

urllib3.disable_warnings()

class sigef:

    def __init__(self, cpf, thresholds=110):
        self.cpf = check_document(cpf).formatted_document
        self.thresholds = thresholds

    def consultar_sigef(self):

        error = True

        attempt = 0
        print('Trying to solve captcha...')
        while(error != False):

            attempt += 1
            print('  -- Attempt {0:02d}'.format(attempt), end='\r')

            url = 'https://sigef.incra.gov.br/consultar/parcelas/'

            s = Session()

            headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                       'Accept-Encoding': 'gzip, deflate, br',
                       'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                       'Connection': 'keep-alive',
                       'Upgrade-Insecure-Requests': '1',
                       'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}

            payload = {'pesquisa_avancada': 'True',
                       'cpf_cnpj': self.cpf}

            s.headers = headers
            s.params = payload
            s.verify = False

            req = s.get(url)

            cookies = req.cookies
            soup = bs(req.text, 'html.parser')
            inputs = soup.select('input')
            d_inputs = {i['name']: i.get('value', '') for i in inputs}

            s.params = d_inputs
            s.cookies = cookies

            url_captcha = 'https://sigef.incra.gov.br/captcha/image/'
            img = s.get(url_captcha + d_inputs.get('captcha_0')).content
            img = BytesIO(img)

            captcha = resolve_captcha(img, self.thresholds)
            captcha = captcha.text_from_captcha()

            d_inputs.update({'captcha_1': captcha})
            s.params = d_inputs

            url = s.get(url).url
            out = s.get(url)

            soup = bs(out.text, 'html.parser')

            try:
                error = soup.find_all('p', {'class': 'help-block error'})[0].get_text()
            except:
                print('\nCaptcha solved!')
                error = False
                break

        tables = []

        try:

            error = soup.find_all('div', {'class': 'alert alert-info alert-block'})[0].get_text()
            print('There were no glebes linked to the CPF.')
            table = None

        except:

            print('Writting the table...')
            codes = list(set(map(lambda x: x['href'], soup.find_all('a', {'title': 'Visualizar detalhes...'}))))

            for c in codes:
                data = pd.read_html(s.get('https://sigef.incra.gov.br' + c).content, encoding='utf_8')
                id = 'P{:03d}'.format(codes.index(c + 1))
                dum0 = data[4]
                dum1 = data[0]
                dum2 = data[3].iloc[:5,]
                dum3 = data[5]
                dum0 = pd.DataFrame({id: dum0.iloc[0].values}, index=dum0.columns.values)
                dum1 = pd.DataFrame({id: dum1[1].values}, index=dum1[0].values)
                dum2 = pd.DataFrame({id: dum2[1].values}, index=dum2[0].values)
                dum3 = pd.DataFrame({id: dum3[1].values}, index=dum3[0].values)
                dum1.replace('Situação', 'Situação da Certificação', inplace=True)
                dum2.replace('Situação', 'Situação do Registro', inplace=True)
                dum2.replace('Denominação', 'Nome da fazenda', inplace=True)
                out = pd.concat([dum0, dum1, dum2, dum3], axis=0)
                tables.append(out)

            table = pd.concat(tables, axis=1).T

        return table

        print('Done!')

teste = sigef(cpf='078.489.099-48')
teste.consultar_sigef()
