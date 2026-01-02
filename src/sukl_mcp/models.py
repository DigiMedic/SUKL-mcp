"""
Pydantic modely pro SÚKL MCP Server.

Definuje datové struktury pro léčivé přípravky, lékárny, úhrady a dostupnost.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RegistrationStatus(str, Enum):
    """Stav registrace léčivého přípravku."""

    REGISTERED = "R"  # Registrovaný
    CANCELLED = "B"  # Zrušená registrace
    EXPIRED = "C"  # Propadlá registrace
    PARALLEL_IMPORT = "P"  # Souběžný dovoz
    PARALLEL_DISTRIBUTION = "D"  # Souběžná distribuce


class DispensationMode(str, Enum):
    """Režim výdeje léčiva."""

    PRESCRIPTION = "Rp"  # Na předpis
    PRESCRIPTION_RESTRICTED = "Rp/o"  # Na předpis s omezením
    OTC = "F"  # Volně prodejné
    PHARMACY_ONLY = "Lp"  # Pouze v lékárně
    RESERVED = "V"  # Vyhrazené


class AvailabilityStatus(str, Enum):
    """Stav dostupnosti léčivého přípravku."""

    AVAILABLE = "available"  # DODAVKY = "1"
    UNAVAILABLE = "unavailable"  # DODAVKY = "0"
    UNKNOWN = "unknown"  # Chybějící nebo neplatná data


# === Modely pro léčivé přípravky ===


class MedicineSearchResult(BaseModel):
    """Výsledek vyhledávání léčivého přípravku."""

    sukl_code: str = Field(..., description="Kód SÚKL (7 číslic)")
    name: str = Field(..., description="Název přípravku")
    supplement: str | None = Field(None, description="Doplněk názvu")
    strength: str | None = Field(None, description="Síla přípravku")
    form: str | None = Field(None, description="Léková forma")
    package: str | None = Field(None, description="Velikost balení")
    atc_code: str | None = Field(None, description="ATC kód")
    registration_status: str | None = Field(None, description="Stav registrace")
    dispensation_mode: str | None = Field(None, description="Režim výdeje")
    is_available: bool | None = Field(None, description="Dostupnost na trhu")

    # Cenové údaje (EPIC 3: Price & Reimbursement)
    has_reimbursement: bool | None = Field(None, description="Má úhradu")
    max_price: float | None = Field(None, description="Maximální cena")
    patient_copay: float | None = Field(None, description="Doplatek pacienta")

    # Match metadata (EPIC 2: Smart Search)
    match_score: float | None = Field(None, description="Relevance skóre (0-100)")
    match_type: str | None = Field(
        None, description="Typ matchování: substance/exact/substring/fuzzy"
    )


class MedicineDetail(BaseModel):
    """Detailní informace o léčivém přípravku."""

    # Základní identifikace
    sukl_code: str = Field(..., description="Kód SÚKL")
    name: str = Field(..., description="Název přípravku")
    supplement: str | None = Field(None, description="Doplněk názvu")

    # Složení a forma
    strength: str | None = Field(None, description="Síla")
    form: str | None = Field(None, description="Léková forma")
    route: str | None = Field(None, description="Cesta podání")
    package_size: str | None = Field(None, description="Velikost balení")
    package_type: str | None = Field(None, description="Typ obalu")

    # Registrace
    registration_number: str | None = Field(None, description="Registrační číslo")
    registration_status: str | None = Field(None, description="Stav registrace")
    registration_holder: str | None = Field(None, description="Držitel rozhodnutí")

    # Klasifikace
    atc_code: str | None = Field(None, description="ATC kód")
    atc_name: str | None = Field(None, description="Název ATC skupiny")
    dispensation_mode: str | None = Field(None, description="Režim výdeje")

    # Dostupnost
    is_available: bool | None = Field(None, description="Aktuálně dostupný")
    is_marketed: bool | None = Field(None, description="Uváděn na trh")

    # Úhrady
    has_reimbursement: bool | None = Field(None, description="Hrazen pojišťovnou")
    max_price: float | None = Field(None, description="Maximální cena")
    reimbursement_amount: float | None = Field(None, description="Výše úhrady")
    patient_copay: float | None = Field(None, description="Doplatek pacienta")

    # Dokumenty
    pil_available: bool = Field(False, description="Příbalový leták dostupný")
    spc_available: bool = Field(False, description="SPC dostupný")

    # Speciální příznaky
    is_narcotic: bool = Field(False, description="Omamná látka")
    is_psychotropic: bool = Field(False, description="Psychotropní látka")
    is_doping: bool = Field(False, description="Doping")

    last_updated: datetime | None = Field(None, description="Poslední aktualizace")


class PILContent(BaseModel):
    """Obsah příbalového letáku (PIL) nebo SPC."""

    sukl_code: str
    medicine_name: str
    document_url: str | None = Field(None, description="URL dokumentu")
    language: str = Field("cs", description="Jazyk dokumentu")
    full_text: str | None = Field(None, description="Extrahovaný text dokumentu")
    document_format: str | None = Field(None, description="Formát dokumentu (pdf, docx)")


class AlternativeMedicine(BaseModel):
    """Alternativní léčivý přípravek (EPIC 4: Availability & Alternatives)."""

    sukl_code: str = Field(..., description="Kód SÚKL alternativy")
    name: str = Field(..., description="Název alternativního přípravku")
    strength: str | None = Field(None, description="Síla (např. '500mg')")
    form: str | None = Field(None, description="Léková forma (tableta, sirup, atd.)")
    is_available: bool = Field(True, description="Je dostupný na trhu")
    has_reimbursement: bool | None = Field(None, description="Má úhradu pojišťovny")
    relevance_score: float = Field(..., description="Relevance skóre 0-100")
    match_reason: str = Field(..., description="Důvod doporučení")
    max_price: float | None = Field(None, description="Maximální cena")
    patient_copay: float | None = Field(None, description="Doplatek pacienta")


class AvailabilityInfo(BaseModel):
    """Informace o dostupnosti léčivého přípravku."""

    sukl_code: str
    name: str = Field(..., description="Název přípravku")
    is_available: bool = Field(..., description="Je dostupný")
    status: AvailabilityStatus = Field(..., description="Stav dostupnosti")
    alternatives_available: bool = Field(False, description="Existují alternativy")
    alternatives: list[AlternativeMedicine] = Field(
        default_factory=list, description="Seznam alternativních léčiv"
    )
    recommendation: str | None = Field(None, description="Doporučení pro uživatele")
    checked_at: datetime = Field(default_factory=datetime.now)


class ReimbursementInfo(BaseModel):
    """Informace o úhradě léčivého přípravku."""

    sukl_code: str
    medicine_name: str
    is_reimbursed: bool = Field(..., description="Je hrazen")
    reimbursement_group: str | None = Field(None, description="Úhradová skupina")
    max_producer_price: float | None = Field(None, description="Max. cena výrobce")
    max_retail_price: float | None = Field(None, description="Max. cena v lékárně")
    reimbursement_amount: float | None = Field(None, description="Výše úhrady")
    patient_copay: float | None = Field(None, description="Doplatek pacienta")
    has_indication_limit: bool = Field(False, description="Indikační omezení")
    indication_limit_text: str | None = Field(None, description="Text omezení")
    specialist_only: bool = Field(False, description="Pouze specialista")


# === Modely pro lékárny ===


class PharmacyInfo(BaseModel):
    """Informace o lékárně."""

    pharmacy_id: str = Field(..., description="ID lékárny")
    name: str = Field(..., description="Název lékárny")

    # Adresa
    street: str | None = Field(None, description="Ulice a číslo")
    city: str = Field(..., description="Město")
    postal_code: str | None = Field(None, description="PSČ")
    district: str | None = Field(None, description="Okres")
    region: str | None = Field(None, description="Kraj")

    # Kontakt
    phone: str | None = Field(None, description="Telefon")
    email: str | None = Field(None, description="E-mail")
    web: str | None = Field(None, description="Web")

    # GPS
    latitude: float | None = Field(None, description="Zeměpisná šířka")
    longitude: float | None = Field(None, description="Zeměpisná délka")

    # Provoz
    operator: str | None = Field(None, description="Provozovatel")

    # Služby
    has_24h_service: bool = Field(False, description="Nepřetržitý provoz")
    has_internet_sales: bool = Field(False, description="Internetový prodej")
    has_preparation_lab: bool = Field(False, description="Přípravna")

    # Stav
    is_active: bool = Field(True, description="Aktivní provoz")


# === API Response modely ===


class SearchResponse(BaseModel):
    """Odpověď na vyhledávací dotaz."""

    query: str
    total_results: int
    results: list[MedicineSearchResult]
    search_time_ms: float | None = None
    match_type: str | None = Field(
        None, description="Typ matchování: substance/exact/substring/fuzzy/none"
    )
