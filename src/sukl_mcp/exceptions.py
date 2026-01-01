"""Custom exception types pro SÚKL MCP server."""


class SUKLException(Exception):
    """Základní exception pro všechny SÚKL chyby."""

    pass


class SUKLValidationError(SUKLException):
    """Chyba validace vstupu (neplatný query, SÚKL kód, atd.)."""

    pass


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
