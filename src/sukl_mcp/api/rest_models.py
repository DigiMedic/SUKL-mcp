"""
Pydantic modely pro SÚKL REST API responses (prehledy.sukl.cz/v1).

Tyto modely mapují přesně strukturu odpovědí z testovaných REST API endpointů.
"""

from typing import Any, List

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# POST /dlprc - Seznam léčivých přípravků (REGISTERED)
# =============================================================================


class LecivaForma(BaseModel):
    """Léková forma."""

    kod: str = Field(..., description="Kód lékové formy")
    nazev: dict[str, str] = Field(..., description="Název v češtině a angličtině")


class CestaPodani(BaseModel):
    """Cesta podání."""

    kod: str = Field(..., description="Kód cesty podání")
    nazev: dict[str, str] = Field(..., description="Název v češtině a angličtině")


class ATCInfo(BaseModel):
    """ATC klasifikace."""

    kod: str = Field(..., description="ATC kód")
    nazev: dict[str, str] = Field(..., description="Název v češtině a angličtině")


class LecivyPripravekDLP(BaseModel):
    """Léčivý přípravek z POST /dlprc endpointu."""

    model_config = ConfigDict(extra="allow")

    # Identifikace
    registracniCisloDisplay: str | None = Field(default=None, description="Registrační číslo pro zobrazení")
    registracniCislo: str | None = Field(default=None, description="Registrační číslo")
    kodSUKL: str = Field(..., description="Kód SÚKL")
    nazevLP: str = Field(..., description="Název léčivého přípravku")
    doplnekNazvu: str | None = Field(default=None, description="Doplněk názvu")

    # Složení a forma
    sila: str | None = Field(default=None, description="Síla přípravku")
    lekovaForma: LecivaForma | None = Field(default=None, description="Léková forma")
    cestaPodani: CestaPodani | None = Field(default=None, description="Cesta podání")

    # Registrace a výdej
    stavRegistrace: str | None = Field(default=None, description="Stav registrace (R, N, Z, atd.)")
    jeRegulovany: bool | None = Field(default=None, description="Je regulovaný")
    jeDodavka: bool | None = Field(default=None, description="Je v aktivním výskytu na trhu")
    uhrada: str | None = Field(default=None, description="Kód úhrady (A, B, D, atd.)")
    dovoz: str | None = Field(default=None, description="Dovoz")
    dostupnost: str | None = Field(default=None, description="Dostupnost (D - dostupný)")
    atc: ATCInfo | None = Field(default=None, description="ATC klasifikace")
    zpusobVydeje: str | None = Field(default=None, description="Způsob výdeje (R - na recept)")


class DLPResponse(BaseModel):
    """Odpověď z POST /dlprc endpointu."""

    data: List[LecivyPripravekDLP] = Field(
        default_factory=list, description="Seznam léčivých přípravků"
    )
    celkem: int = Field(..., description="Celkový počet záznamů")
    extraSearch: List[Any] = Field(default_factory=list, description="Další možnosti vyhledávání")


# =============================================================================
# GET /lekarny - Seznam lékáren
# =============================================================================


class Adresa(BaseModel):
    """Adresa."""

    obec: str | None = Field(default=None, description="Obec")
    castObce: str | None = Field(default=None, description="Část obce")
    ulice: str | None = Field(default=None, description="Ulice")
    cisloPopisne: str | None = Field(default=None, description="Číslo popisné")
    cisloOrientacni: str | None = Field(default=None, description="Číslo orientační")
    psc: str | None = Field(default=None, description="PSČ")
    kod_obce: str | None = Field(default=None, description="Kód obce")
    kod_okresu: str | None = Field(default=None, description="Kód okresu")
    nazev_okresu: str | None = Field(default=None, description="Název okresu")


class VedouciLekarnik(BaseModel):
    """Vedoucí lékárník."""

    jmeno: str = Field(..., description="Jméno")
    prijmeni: str = Field(..., description="Příjmení")
    titulPred: str | None = Field(default=None, description="Titul před jménem")
    titulZa: str | None = Field(default=None, description="Titul za jménem")


class Kontakty(BaseModel):
    """Kontaktní údaje."""

    telefon: List[str] = Field(default_factory=list, description="Telefonní čísla")
    email: List[str] = Field(default_factory=list, description="E-mailové adresy")
    web: List[str] = Field(default_factory=list, description="Webové stránky")


class Geo(BaseModel):
    """Geografické údaje."""

    lat: float = Field(..., description="Zeměpisná šířka")
    lon: float = Field(..., description="Zeměpisná délka")


class OteviraciDoba(BaseModel):
    """Otevírací doba."""

    den: str = Field(..., description="Den v týdnu")
    od: str | None = Field(default=None, description="Od")
    do: str | None = Field(default=None, description="Do")


class Lekarna(BaseModel):
    """Lékárna."""

    model_config = ConfigDict(extra="allow")

    # Základní informace
    nazev: str | None = Field(default=None, description="Název lékárny")
    kodPracoviste: str | None = Field(default=None, description="Kód pracoviště")
    kodLekarny: str | None = Field(default=None, description="Kód lékárny")
    icz: str | None = Field(default=None, description="IČZ")
    ico: str | None = Field(default=None, description="IČO")
    typLekarny: str | None = Field(default=None, description="Typ lékárny")

    # Adresa a kontakty
    adresa: Adresa | None = Field(default=None, description="Adresa")
    vedouciLekarnik: VedouciLekarnik | None = Field(default=None, description="Vedoucí lékárník")
    kontakty: Kontakty | None = Field(default=None, description="Kontaktní údaje")

    # GPS a otevírací doba
    geo: Geo | None = Field(default=None, description="GPS souřadnice")
    oteviraciDoba: List[OteviraciDoba] | None = Field(default=None, description="Otevírací doba")


class LekarnyResponse(BaseModel):
    """Odpověď z GET /lekarny endpointu."""

    data: List[Lekarna] = Field(default_factory=list, description="Seznam lékáren")
    celkem: int = Field(..., description="Celkový počet lékáren")


# =============================================================================
# GET /ciselniky - Číselníky
# =============================================================================


class CiselnikPolozka(BaseModel):
    """Položka číselníku."""

    kod: str = Field(..., description="Kód")
    nazev: str = Field(..., description="Název")
    nazevEN: str | None = Field(default=None, description="Název v angličtině")


class CiselnikResponse:
    """Odpověď z číselníkových endpointů."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, list):
            return v
        return []


# =============================================================================
# GET /datum-aktualizace - Datum aktualizace dat
# =============================================================================


class DatumAktualizace(BaseModel):
    """Datum aktualizace dat v databázi."""

    DLPO: str | None = Field(default=None, description="Datum aktualizace léčivých přípravků")
    DLPW: str | None = Field(default=None, description="Datum aktualizace skladových zásob")
    SCAU: str | None = Field(default=None, description="Datum aktualizace cen a úhrad")


# =============================================================================
# Utility modely
# =============================================================================


class APIError(BaseModel):
    """Chybová odpověď z API."""

    kodChyby: int = Field(..., description="Kód chyby")
    popisChyby: str = Field(..., description="Popis chyby")
    detailChyby: List[dict[str, Any]] = Field(default_factory=list, description="Detail chyby")


# =============================================================================
# Validace pro POST /dlprc
# =============================================================================


class DLPSearchParams(BaseModel):
    """Parametry pro POST /dlprc vyhledávání."""

    atc: str | None = Field(default=None, description="ATC kód (např. 'A10AE04')")
    stavRegistrace: str | None = Field(default=None, description="Stav registrace (R, N, Z, atd.)")
    uhrada: str | None = Field(default=None, description="Kód úhrady (A, B, D, atd.)")
    jeDodavka: bool | None = Field(default=None, description="Pouze přípravky s aktivním výskytem na trhu")
    jeRegulovany: bool | None = Field(default=None, description="Pouze regulované přípravky")
    stranka: int = Field(1, ge=1, description="Číslo stránky (default: 1)")
    pocet: int = Field(10, ge=1, le=1000, description="Počet záznamů na stránku (default: 10)")
