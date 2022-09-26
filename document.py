import re
import numpy as np


class check_document:

    def __init__(self, document_number):
        self.document_number = document_number
        self.document_digits = self.__getdigits()
        self.document_type = self.__document_type()
        self.isvalid = self.__isvalid()
        self.formatted_document = self.__format_document()
        self.isdocument = self.__isdocument()


    def __getdigits(self):
        doc = re.sub('[^0-9]*', '', str(self.document_number))
        if (len(doc) >= 5) & (len(doc) <= 11):
            doc = '{:011d}'.format(int(doc))
        elif (len(doc) > 11) & (len(doc) <= 14):
            doc = '{:014d}'.format(int(doc))
        else:
            doc = None
        return doc


    def __document_type(self):
        ndigits = len(self.document_digits)
        return ('CPF' if ndigits == 11 else None) if ndigits != 14 else 'CNPJ'


    def __isvalid(self):
        doc = [int(x) for x in list(self.document_digits)]
        if self.document_type is not None:
            if len(np.unique(doc)) != 1:
                if self.document_type == 'CPF':
                    d1 = (10 * np.sum(np.array(doc[0:9]) * np.arange(10, 1, -1))) % 11
                    d1 = d1 if d1 < 10 else 0
                    d2 = (10 * np.sum(np.array(doc[0:9] + [d1]) * np.arange(11, 1, -1))) % 11
                    d2 = d2 if d2 < 10 else 0
                    return True if (d1 == doc[-2]) & (d2 == doc[-1]) else False
                else:
                    d1 = (10 * np.sum(doc[0:12] * np.concatenate((np.arange(5, 1, -1), np.arange(9, 1, -1)), axis=0))) % 11
                    d1 = d1 if d1 < 10 else 0
                    d2 = (10 * np.sum(np.array(doc[0:12] + [d1]) * np.concatenate((np.arange(6, 1, -1), np.arange(9, 1, -1)), axis=0))) % 11
                    d2 = d2 if d2 < 10 else 0
                    return True if (d1 == doc[-2]) & (d2 == doc[-1]) else False
            else:
                return False
        else:
            return None


    def __format_document(self):
        doc = self.document_digits if self.document_type is not None else None
        if doc is not None:
            if len(str(doc)) <= 11:
                doc = '{:011d}'.format(int(doc))
                p1 = int(str(doc)[0:3])
                p2 = int(str(doc)[3:6])
                p3 = int(str(doc)[6:9])
                p4 = int(str(doc)[9:])
                return '{0:03d}.{1:03d}.{2:03d}-{3:02d}'.format(p1, p2, p3, p4)
            else:
                x = '{:014d}'.format(int(doc))
                p1 = int(str(doc)[0:2])
                p2 = int(str(doc)[2:5])
                p3 = int(str(doc)[5:8])
                p4 = int(str(doc)[8:12])
                p5 = int(str(doc)[12:])
                return '{0:02d}.{1:03d}.{2:03d}/{3:04d}-{4:02d}'.format(p1, p2, p3, p4, p5)
        else:
            return None


    def __isdocument(self):
        return False if None in [self.document_type, self.isvalid, self.formatted_document] else True
