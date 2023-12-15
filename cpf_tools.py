from dataclasses import dataclass, field
import re

class CPFFormatter:
    """
    A class used to manipulate and validate CPF numbers.
    
    ...

    Attributes
    ----------
    digits : str
        The digits of the CPF number after formatting.

    Methods
    -------
    get_digits(cpf: int | str) -> str:
        Returns the CPF number without formatting.
    validate() -> bool:
        Validates the CPF number.
    formatter() -> str:
        Formats the CPF number with dots and hyphen.
    doc_from_uf() -> str:
        Returns the state or group of states from where the CPF was issued.
    """

    def __init__(self, cpf: int | str) -> None:
        """
        Constructs all the necessary attributes for the CPFFormatter object.

        Parameters
        ----------
            cpf : int | str
                The CPF number to be manipulated and validated.
        """
        self.digits = self.get_digits(cpf)

    def get_digits(self, cpf) -> str:
        """
        Returns the CPF number without formatting.

        Parameters
        ----------
            cpf : int | str
                The CPF number to be manipulated.

        Returns
        -------
        str
            The CPF number without formatting.
        """
        numbers = re.sub("\D+", "", str(cpf))
        if numbers == "":
            raise ValueError("Provide a numeric or formatted CPF number.")
        return f"{int(numbers):011d}"

    def validate(self) -> bool:
        """
        Validates the CPF number.

        Returns
        -------
        bool
            True if the CPF number is valid, False otherwise.
        """
        ndoc = self.digits

        # Checks if the CPF number is a sequence of repeated digits
        known_invalids = [11 * str(i) for i in range(10)]

        if ndoc in known_invalids:
            return False

        i = 0
        while i < 2:
            ndoc_enum = zip(range(10, 1, -1), ndoc[i:9+i])
            resto = sum(int(x[1])*x[0] for x in ndoc_enum) % 11
            dv = 0 if resto < 2 else 11 - resto
            if int(dv) != int(ndoc[-2+i]):
                return False
            i += 1
        return True

    def formatter(self) -> str:
        """
        Formats the CPF number with dots and hyphen.

        Returns
        -------
        str
            The formatted CPF number.
        """
        ndoc = self.digits
        return f"{ndoc[:3]}.{ndoc[3:6]}.{ndoc[6:9]}-{ndoc[9:]}"

    def doc_from_uf(self) -> str:
        """
        Returns the state or group of states from where the CPF was issued.

        Returns
        -------
        str
            The state or group of states.
        """
        if not self.validate():
            return "Invalid CPF"

        # The last digit before the two checker digits of the CPF number represent the state or group of states
        states = {
            "0": "Rio Grande do Sul",
            "1": "Distrito Federal, Goiás, Mato Grosso, Mato Grosso do Sul e Tocantins",
            "2": "Amazonas, Pará, Roraima, Amapá, Acre e Rondônia",
            "3": "Ceará, Maranhão e Piauí",
            "4": "Paraíba, Pernambuco, Alagoas e Rio Grande do Norte",
            "5": "Bahia e Sergipe",
            "6": "Minas Gerais",
            "7": "Rio de Janeiro e Espírito Santo",
            "8": "São Paulo",
            "9": "Paraná e Santa Catarina",
        }

        return states.get(self.digits[-3], "Unknown")


from dataclasses import dataclass, field

@dataclass(order=True)
class CPF:
    """
    A class used to represent a CPF number.

    ...

    Attributes
    ----------
    cpf : int | str
        The CPF number to be manipulated and validated.
    digits : str
        The digits of the CPF number before formatting.
    formatted : str
        The formatted CPF number.
    isvalid : bool
        The validation status of the CPF number.
    uf : str
        The state or group of states from where the CPF was issued.
    """

    cpf: int | str
    digits: str = field(init=False)
    formatted: str = field(init=False)
    isvalid: bool = field(init=False)
    uf: str = field(init=False)
    
    def __post_init__(self) -> None:
        """
        Initializes the attributes of the CPF object after it's created.

        This method is automatically called after the object is created and
        it uses the CPFFormatter class to manipulate and validate the CPF number.
        """
        data = CPFFormatter(self.cpf)
        self.digits = data.digits
        self.formatted = data.formatter()
        self.isvalid = data.validate()
        self.uf = data.doc_from_uf()
