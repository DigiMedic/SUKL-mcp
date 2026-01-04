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


class ATCChild(BaseModel):
    """Potomek ATC skupiny."""

    code: str = Field(..., description="ATC kód podskupiny")
    name: str = Field(..., description="Název podskupiny")


class ATCInfo(BaseModel):
    """Informace o ATC (anatomicko-terapeuticko-chemické) skupině."""

    code: str = Field(..., description="ATC kód skupiny (1-7 znaků)")
    name: str = Field(..., description="Název ATC skupiny")
    level: int = Field(
        ...,
        ge=1,
        le=5,
        description="Úroveň v ATC hierarchii (1=anatomická, 5=chemická látka)",
    )
    children: list[ATCChild] = Field(default_factory=list, description="Seznam podskupin (max 20)")
    total_children: int = Field(0, description="Celkový počet podskupin")


# === Modely pro nedostupné léčivé přípravky (HSZ) ===


class UnavailabilityType(str, Enum):
    """Typ nedostupnosti léčivého přípravku."""

    ONE_TIME = "JR"  # Jednorázový požadavek
    LIMITED = "OOP"  # Omezená dostupnost


class UnavailableMedicineInfo(BaseModel):
    """Informace o nedostupném léčivém přípravku."""

    sukl_code: str = Field(..., description="Kód SÚKL (7 číslic)")
    name: str = Field(..., description="Název přípravku")
    supplement: str | None = Field(None, description="Doplněk názvu")
    unavailability_type: UnavailabilityType = Field(..., description="Typ nedostupnosti (JR/OOP)")
    valid_from: datetime | None = Field(None, description="Platnost od")
    valid_to: datetime | None = Field(None, description="Platnost do")
    reporting_frequency: str | None = Field(
        None, description="Periodicita hlášení (denně/týdně/měsíčně)"
    )
    required_reporters: list[str] = Field(
        default_factory=list,
        description="Skupiny povinných hlásitelů (lékárny/distributoři/MAH)",
    )


class UnavailabilityReport(BaseModel):
    """Souhrnná zpráva o nedostupných léčivých přípravcích."""

    total_count: int = Field(..., description="Celkový počet nedostupných LP")
    one_time_requests: int = Field(0, description="Počet jednorázových požadavků (JR)")
    limited_availability: int = Field(0, description="Počet s omezenou dostupností (OOP)")
    medicines: list[UnavailableMedicineInfo] = Field(
        default_factory=list, description="Seznam nedostupných LP"
    )
    checked_at: datetime = Field(default_factory=datetime.now)


# === Modely pro market report ===


class MarketNotificationType(str, Enum):
    """Typ oznámení o uvádění LP na trh."""

    STARTED = "zahajeni"  # Zahájení uvádění na trh
    SUSPENDED = "preruseni"  # Přerušení uvádění
    RESUMED = "obnoveni"  # Obnovení uvádění
    TERMINATED = "ukonceni"  # Ukončení uvádění


class MarketReportInfo(BaseModel):
    """Informace o uvádění léčivého přípravku na trh."""

    sukl_code: str = Field(..., description="Kód SÚKL (7 číslic)")
    notification_type: MarketNotificationType = Field(..., description="Typ oznámení")
    valid_from: datetime | None = Field(None, description="Platnost od")
    reported_at: datetime | None = Field(None, description="Datum hlášení")
    replacement_medicines: list[str] = Field(
        default_factory=list, description="Náhradní přípravky (SÚKL kódy)"
    )
    suspension_reason: str | None = Field(None, description="Důvod přerušení")
    expected_resume_date: datetime | None = Field(None, description="Očekávané obnovení")
    note: str | None = Field(None, description="Poznámka")


# === Modely pro distributory ===


class DistributorInfo(BaseModel):
    """Informace o distributorovi léčiv."""

    workplace_code: str = Field(..., description="Kód pracoviště (11 číslic)")
    name: str = Field(..., description="Název distributora")
    ico: str = Field(..., description="IČO")
    type: str = Field(..., description="Typ pracoviště (Sklad, apod.)")

    # Adresa pracoviště
    street: str | None = Field(None, description="Ulice a číslo")
    city: str | None = Field(None, description="Město")
    postal_code: str | None = Field(None, description="PSČ")
    country: str = Field("CZ", description="Země")

    # Povolení
    has_sukl_permit: bool = Field(False, description="Povolení SÚKL")
    has_eu_permit: bool = Field(False, description="Povolení EU")
    has_dispensing_permit: bool = Field(False, description="Povolení výdeje")

    # Kontakty
    phone: list[str] = Field(default_factory=list, description="Telefonní čísla")
    email: list[str] = Field(default_factory=list, description="E-mailové adresy")
    web: list[str] = Field(default_factory=list, description="Webové stránky")

    # Aktivní stav
    is_active: bool = Field(True, description="Aktivní provoz")


# === Modely pro šarže vakcín ===


class VaccineBatchInfo(BaseModel):
    """Informace o propuštěné šarži vakcíny."""

    sukl_code: str = Field(..., description="Kód SÚKL vakcíny")
    vaccine_name: str | None = Field(None, description="Název vakcíny")
    batch_number: str = Field(..., description="Číslo šarže")
    released_date: datetime | None = Field(None, description="Datum propuštění")
    expiration_date: datetime | None = Field(None, description="Datum expirace")


class VaccineBatchReport(BaseModel):
    """Souhrnná zpráva o šaržích vakcín."""

    total_batches: int = Field(..., description="Celkový počet šarží")
    last_update: datetime | None = Field(None, description="Datum poslední aktualizace")
    batches: list[VaccineBatchInfo] = Field(default_factory=list, description="Seznam šarží")
