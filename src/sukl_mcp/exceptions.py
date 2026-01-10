"""Custom exception types pro SÚKL MCP server."""


class SUKLException(Exception):
    """Základní exception pro všechny SÚKL chyby."""

    pass


class SUKLValidationError(SUKLException):
    """Chyba validace vstupu (neplatný query, SÚKL kód, atd.)."""

    pass


class SUKLAPIError(SUKLException):
    """Chyba při komunikaci s SÚKL REST API."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class SUKLZipBombError(SUKLException):
    """ZIP bomb detekována - příliš velký soubor."""

    pass


class SUKLDataError(SUKLException):
    """Chyba při načítání nebo zpracování dat."""

    pass


class SUKLDocumentError(SUKLException):
    """Chyba při stahování nebo zpracování dokumentu (PIL/SPC)."""

    pass


class SUKLParseError(SUKLDocumentError):
    """Chyba při parsování dokumentu (PDF/DOCX)."""

    pass
