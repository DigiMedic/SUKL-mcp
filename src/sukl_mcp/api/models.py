"""
Pydantic modely pro SÚKL REST API responses.

Tyto modely mapují přesně strukturu odpovědí z prehledy.sukl.cz/dlp/v1/
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class APILecivyPripravek(BaseModel):
    """
    Model pro odpověď z /dlp/v1/lecive-pripravky/{sukl_kod}.

    Mapuje přesně JSON strukturu z SÚKL API.
    """

    model_config = ConfigDict(extra="allow")  # Povolit další pole z API

    # Základní identifikace
    kodSUKL: str = Field(..., description="SÚKL kód léčiva (7 číslic)")
    nazev: str = Field(..., description="Název léčivého přípravku")
    registrovanyNazevLP: str | None = Field(None, description="Registrovaný název")

    # Složení a forma
    sila: str | None = Field(None, description="Síla přípravku (např. '500MG')")
    lekovaFormaKod: str | None = Field(None, description="Kód lékové formy")
    baleni: str | None = Field(None, description="Velikost balení")
    doplnek: str | None = Field(None, description="Doplněk názvu")
    obalKod: str | None = Field(None, description="Kód obalu")
    cestaKod: str | None = Field(None, description="Cesta podání")

    # Registrace
    stavRegistraceKod: str | None = Field(None, description="Stav registrace (R=registrován)")
    registracniCislo: str | None = Field(None, description="Registrační číslo")
    registracniProceduraKod: str | None = Field(None, description="Typ registrace (NAR=národní)")
    datumRegistrace: str | None = Field(None, description="Datum registrace")
    registracePlatDo: str | None = Field(None, description="Platnost registrace do")
    neomezenaPlatReg: bool = Field(False, description="Neomezená platnost registrace")

    # Držitel
    drzitelKod: str | None = Field(None, description="Kód držitele registrace")
    zemeDrziteleKod: str | None = Field(None, description="Země držitele")
    aktualniDrzitelKod: str | None = Field(None, description="Aktuální držitel")

    # ATC klasifikace
    ATCkod: str | None = Field(None, description="ATC kód (anatomicko-terapeutický)")
    indikacniSkupinaKod: int | None = Field(None, description="Indikační skupina")

    # Účinné látky
    leciveLatky: list[int] = Field(default_factory=list, description="ID účinných látek")

    # DDD (Definovaná denní dávka)
    dddMnozstvi: float | None = Field(None, description="DDD množství")
    dddMnozstviJednotka: str | None = Field(None, description="Jednotka DDD")
    dddBaleni: float | None = Field(None, description="DDD na balení")
    dddZdroj: str | None = Field(None, description="Zdroj DDD")

    # Výdej a omezení
    zpusobVydejeKod: str | None = Field(None, description="Způsob výdeje (V=na předpis)")
    zavislostKod: str | None = Field(None, description="Návykovost")
    dopingKod: str | None = Field(None, description="Dopingová látka")
    narizeniVladyKod: str | None = Field(None, description="Nařízení vlády")
    omezeniPreskripceSmp: bool = Field(False, description="Omezení preskripce SMP")

    # Dostupnost
    jeDodavka: bool = Field(False, description="Je aktuálně dodáván")

    # Další
    braillovoPismo: str | None = Field(None, description="Braillovo písmo")
    expirace: str | None = Field(None, description="Expirace")
    expiraceJednotka: str | None = Field(None, description="Jednotka expirace")
    MRPcislo: str | None = Field(None, description="MRP číslo")
    pravniZakladRegistraceKod: str | None = Field(None, description="Právní základ")
    ochrannePrvky: bool = Field(False, description="Ochranné prvky")
    jazykObalu: str | None = Field(None, description="Jazyk obalu")
    povinneVzorky: bool = Field(False, description="Povinné vzorky")


class APICena(BaseModel):
    """Model pro cenové informace z API."""

    model_config = ConfigDict(extra="allow")

    kodSUKL: str
    cenaVyrobce: float | None = None
    cenaOriginalni: float | None = None
    cenaPuvodce: float | None = None
    dphSazba: float | None = None
    maxCenaDistribuce: float | None = None
    maxCenaLekarna: float | None = None
    uhradaZP: float | None = None
    doplatek: float | None = None


class APIUhrada(BaseModel):
    """Model pro informace o úhradě z API."""

    model_config = ConfigDict(extra="allow")

    kodSUKL: str
    skupinaUhrady: str | None = None
    typUhrady: str | None = None
    zakladniUhrada: float | None = None
    uhradaZP: float | None = None
    doplatek: float | None = None
    omezeniPreskripce: str | None = None
    omezeniIndikace: str | None = None


class APISearchResponse(BaseModel):
    """
    Model pro odpověď z vyhledávání.

    SÚKL API vrací pouze seznam SÚKL kódů při vyhledávání.
    """

    codes: list[str] = Field(default_factory=list, description="Seznam SÚKL kódů")
    total: int = Field(0, description="Celkový počet výsledků")

    @classmethod
    def from_api_response(cls, data: list[str]) -> "APISearchResponse":
        """Vytvoří response z raw API odpovědi."""
        return cls(codes=data, total=len(data))


class APILekarna(BaseModel):
    """Model pro lékárnu z API."""

    model_config = ConfigDict(extra="allow")

    id: str
    nazev: str
    ulice: str | None = None
    cisloPopisne: str | None = None
    obec: str | None = None
    psc: str | None = None
    okres: str | None = None
    kraj: str | None = None
    telefon: str | None = None
    email: str | None = None
    web: str | None = None
    gpsLat: float | None = None
    gpsLon: float | None = None
    typ: str | None = None
    sluzby: list[str] = Field(default_factory=list)


class APIDistributor(BaseModel):
    """Model pro distributora z API."""

    model_config = ConfigDict(extra="allow")

    id: str
    nazev: str
    ico: str | None = None
    ulice: str | None = None
    obec: str | None = None
    psc: str | None = None
    telefon: str | None = None
    email: str | None = None


class APIError(BaseModel):
    """Model pro chybovou odpověď z API."""

    kodChyby: int
    popisChyby: str
    detailChyby: list[dict[str, Any]] = Field(default_factory=list)
