import pandas as pd
import requests
from bs4 import BeautifulSoup
import re


class TEquotes:
    """
    Module for returning quotations for agricultural commodities on the
    Trading Economics platform.
    """

    def __init__(self):
        self.crops = self.__list_crops()
        self.currencies = self.__list_currencies()
        self.convweights = self.__list_conversion_weights()

    def __list_crops(self) -> list:
        """
        Returns a list with all possible quotes for agricultural crops.

        Returns:
        -------
        ['Crop_1', 'Crop_2', ..., 'Crop_n']
        """

        session = requests.Session()

        url = 'https://tradingeconomics.com/forecast/commodity'
        headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64)'}

        req = session.get(url, headers=headers)
        if req.ok:
            soup = BeautifulSoup(req.content, 'html.parser')
            items = [[y.text for y in x.select('b')] for x in soup.select('table')]

            tables = [[y.text for y in x.select('th')][1].strip() for x in soup.select('table')]
            idx = tables.index('Agricultural')

            crops = items[idx]
        else:
            print(f'Error: the server returned the {str(req.status_code)} code error.')
            crops = None

        return crops


    def __list_currencies(self) -> dict:
        """
        Returns a dictionary with all currency conversion possibilities.

        Returns:
        -------
        [
          {'Area_1': {'from': 'CURin_1', 'to': 'CURout_1'}, ..., {'from': 'CURin_n', 'to': 'CURout_n'}},
          {'Area_2': {'from': 'CURin_1', 'to': 'CURout_1'}, ..., {'from': 'CURin_n', 'to': 'CURout_n'}},
          ...
          {'Area_n': {'from': 'CURin_1', 'to': 'CURout_1'}, ..., {'from': 'CURin_n', 'to': 'CURout_n'}}
        ]
        """

        session = requests.Session()

        url = 'https://tradingeconomics.com/forecast/currency'
        headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64)'}

        req = session.get(url, headers=headers)
        if req.ok:
            soup = BeautifulSoup(req.content, 'html.parser')
            items = [[{'from': y.text[:3], 'to': y.text[3:]} for y in x.select('b')] for x in soup.select('table')]
            areas = [[y.text for y in x.select('th')][1].strip() for x in soup.select('table')]
            currencies = {a: c for a, c in zip(areas, items)}
        else:
            print(f'Error: the server returned the {str(req.status_code)} code error.')
            currencies = None

        return currencies


    def __list_conversion_weights(self):

        return {'Soybeans': ['Lbs', 'CWT', 'kg', 't', 'bag60', 'BU'],
                'Wheat':    ['Lbs', 'CWT', 'kg', 't', 'bag60', 'BU'],
                'Corn':     ['Lbs', 'CWT', 'kg', 't', 'bag60', 'BU'],
                'Sorghum':  ['Lbs', 'CWT', 'kg', 't', 'bag60', 'BU'],
                'Barley':   ['Lbs', 'CWT', 'kg', 't', 'bag60', 'BU'],
                'Oat':      ['Lbs', 'CWT', 'kg', 't', 'bag60', 'BU'],
                'Default':  ['Lbs', 'CWT', 'kg', 't', 'bag60']}


    def __get_unit(self, url: str, name: str) -> 'tuple[str, str]':
        """
        Returns a tuple with the name of the agricultural crop and its respective unit.

        Parameters:
        -----------
        Parameter url: the URL to lookup the quote unit
        Parameter name: the name of the crop

        Returns:
        --------
        ('crop_name', 'unit')
        """

        with requests.Session() as session:
            session.headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
            req = session.get(url=url)
            if req.ok:
                soup = BeautifulSoup(req.content, 'html.parser')
                table = soup.find_all('table')[1]
                unit = [[(i.text).strip() for i in row.find_all('td')][1:] for row in table.find_all('tr')][1:][0][5]
                return name, unit
            else:
                print(f'Error: the server returned the {str(req.status_code)} code error.')
                return None


    def crop_quote(self, crop: str) -> dict:
        """
        Returns a list with the quotation of the current and future agricultural
        crop, according to the quartile of the year (1st, 2nd, 3rd, and 4th).

        Parameters:
        -----------
        Parameter crop: the name of the crop to query the quotation

        Returns:
        --------
        [
          {'date': 'today', 'price': float, 'unit': 'XX/XX'},
          {'date': 'QX/XX', 'price': float, 'unit': 'XX/XX'},
          ...
          {'date': 'QX/XX', 'price': float, 'unit': 'XX/XX'}
        ]
        """

        if not crop.title() in self.crops:
            print(f"Warning: Unable to find the '{crop.lower()}' crop. See the crops list to find all the possibilities.")
            return None

        session = requests.Session()

        base = 'https://tradingeconomics.com'
        url = f'{base}/forecast/commodity'

        headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64)'}

        req = session.get(url, headers=headers)

        if req.ok:
            df = pd.read_html(req.content)[2].drop(columns=['Unnamed: 0', 'Signal'])
            df = df.loc[df['Agricultural'] == crop.title()].set_index('Agricultural')
            df = df.T.reset_index()
            df.columns = ['date', 'price']
            df = df.replace({'Price': 'today'})

            soup = BeautifulSoup(req.content, 'html.parser')

            args = [[f"{base}{x['href']}", re.sub('\n', '', x.text)] for x in soup.find_all('a', href=True)]
            args = list(filter(lambda x: f'/commodity/{crop.lower()}' in x[0], args))[0]

            units = self.__get_unit(*args)

            out = [{'date': d, 'price': p, 'unit': units[1]} for d, p in zip(df['date'], df['price'])]
        else:
            print(f'Error: the server returned the {str(req.status_code)} code error.')
            out = None

        return out


    def currency_quote(self, input: str, output: str, area: str = 'Major') -> dict:
        """
        Returns a list with the quotation of the current and future exchange
        rates, according to the quartile of the year (1st, 2nd, 3rd and 4th).

        Parameters:
        -----------
        Parameter input: the currency to be converted (abbrviation)
        Parameter output: the converted currency (abbrviation)
        Parameter area: the large areas in the globe (such as continents or large countries)

        Returns:
        --------
        [
          {'date': 'today', 'price': float, 'from': 'XXX', 'to': 'XXX'},
          {'date': 'QX/XX', 'price': float, 'from': 'XXX', 'to': 'XXX'},
          ...
          {'date': 'QX/XX', 'price': float, 'from': 'XXX', 'to': 'XXX'}
        ]
        """

        base = 'https://tradingeconomics.com'
        url = f'{base}/forecast/currency'
        headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64)'}

        session = requests.Session()

        req = session.get(url, headers=headers)

        if req.ok:
            soup = BeautifulSoup(req.content, 'html.parser')
            a = [re.sub('\r\n\W+', '', x.text).strip() for x in soup.select('th')]
            r = re.compile(r'/|Signal|Price|^$')
            areas = list(filter(lambda x: not r.search(x), a))

            idx = areas.index(area)

            df = pd.read_html(req.content)[idx].drop(columns=['Unnamed: 0', 'Signal'])
            df['input'] = df[area].str.slice(stop=3)
            df['output'] = df[area].str.slice(start=3)
            try:
                df = df.loc[(df['input'] == input) & (df['output'] == output)]
                df = df.drop(columns=['input', 'output', area])
                df = df.T.reset_index()
                df.columns = ['date', 'price']
                df = df.replace({'Price': 'today'})
                out = [{'date': d, 'price': p, 'from': input, 'to': output} for d, p in zip(df['date'], df['price'])]
            except ValueError:
                print(f'Warning: Unable to convert {input} to {output}. See currencies list to find all the possibilities.')
                out = None
        else:
            print(f'Error: the server returned the {str(req.status_code)} code error.')
            out = None

        return out


    def conversion_weights(self, crop: str = 'Default', input: str, output: str) -> float:
        """
        Returns a numeric conversion factor for converting the 'input' to 'output'
        weight unit. Some conversions need to provide the crop name for the correct
        weight unit conversion, such as those involving volumetric unit to mass
        unit conversion.

        Parameters:
        -----------
        Parameter crop: the crop of unit to be converted
        Parameter input: the weight unit to be converted
        Parameter output: the desired weight unit

        Returns:
        --------
        float
        """

        data = {'Soybeans': {'Lbs': 60, 'CWT': 6000, 'kg': 27.216, 't': 0.027216, 'bag60': 0.45360, 'BU': 1},
                'Wheat':    {'Lbs': 60, 'CWT': 6000, 'kg': 27.216, 't': 0.027216, 'bag60': 0.45360, 'BU': 1},
                'Corn':     {'Lbs': 56, 'CWT': 5600, 'kg': 25.402, 't': 0.025402, 'bag60': 0.42334, 'BU': 1},
                'Sorghum':  {'Lbs': 56, 'CWT': 5600, 'kg': 25.402, 't': 0.025402, 'bag60': 0.42334, 'BU': 1},
                'Barley':   {'Lbs': 48, 'CWT': 4800, 'kg': 21.773, 't': 0.021773, 'bag60': 0.36288, 'BU': 1},
                'Oat':      {'Lbs': 32, 'CWT': 3200, 'kg': 14.515, 't': 0.014515, 'bag60': 0.24192, 'BU': 1},
                'Default':  {'Lbs':  1, 'CWT': 100,  'kg': 0.4536, 't': 0.004536, 'bag60': 0.00756}}

        try:
            units = data.get(crop).keys()
            if (input in units) & (output in units):
                out = data.get(crop).get(output) / data.get(crop).get(input)
            else:
                out = None
        except Exception:
            print(f'Warning: Unable to convert {input} to {output}. See convweights list to find all the possibilities.')
            out = None

        return out
