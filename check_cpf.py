import requests
from bs4 import BeautifulSoup
from io import BytesIO
from base64 import b64decode
from resolve_captcha import resolve_captcha
from PIL import Image
from requests_html import HTML, AsyncHTMLSession
from pathlib import Path
import pandas as pd

headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
           'Accept-Encoding': 'gzip, deflate, br',
           'host': 'servicos.receita.fazenda.gov.br',
           'Referer': 'https://servicos.receita.fazenda.gov.br/servicos/cpf/consultasituacao/ConsultaPublicaSonoro.asp',
           'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0'}

url = 'https://servicos.receita.fazenda.gov.br/Servicos/CPF/ConsultaSituacao/ConsultaPublicaSonoro.asp?CPF=05828793705&NASCIMENTO=03081988'

s = requests.Session()

# js_url = 'http://captcha2.servicoscorporativos.serpro.gov.br/js/captcha.serpro.gov.br.js'
# t = BeautifulSoup(s.get(js_url).text, 'html.parser').get_text()
# img = t.split('\n')
# img = pd.Series(img)[['data:image/png;base64' in x for x in img]].str.split('"')
# img = img.apply(lambda x: BytesIO(b64decode(x[1].split(',')[1]))).to_list()
# img = Image.open(img[1])

payload = {'idCheckedReCaptcha': 'false',
           'txtCPF': '03/08/1988',
           'txtDataNascimento':	'058.287.937-05',
           'CPF': '058.287.937-05',
           'NASCIMENTO': '03/08/1988',
           'txtTexto_captcha_serpro_gov_br': '',
           'Enviar': 'Consultar'}


req = requests.get(url, headers=headers)

img = BeautifulSoup(req.content, 'html.parser')
img = img.find_all('img', {'id': 'imgCaptcha'})[0]['src']
img = BytesIO(b64decode(img.split(',')[1]))
Image.open(img)

captcha = resolve_captcha(img, thresholds=50, psm=7).text_from_captcha()
#
# payload = {'idCheckedReCaptcha': 'false',
#            'txtCPF': '058.287.937-05',
#            'txtDataNascimento':	'03/08/1988',
#            'CPF': "058.287.937-05",
#            'NASCIMENTO': "03/08/1988",
#            'txtTexto_captcha_serpro_gov_br': 'sP',
#            'Enviar': 'Consultar'}

payload.update({'txtTexto_captcha_serpro_gov_br': '38Q6rX'})

url = 'https://servicos.receita.fazenda.gov.br/Servicos/CPF/ConsultaSituacao/ConsultaPublicaExibir.asp'
out = s.post(url, data=payload, headers=headers, cookies=req.cookies)

BeautifulSoup(out.content)
