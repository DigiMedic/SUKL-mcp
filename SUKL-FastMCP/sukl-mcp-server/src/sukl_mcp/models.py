"""
Pydantic modely pro SÚKL MCP Server.

Definuje datové struktury pro:
- Léčivé přípravky (medicines)
- Lékárny (pharmacies)
- Úhrady a ceny (reimbursements)
- Dostupnost (availability)
- ATC klasifikace
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


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


class DrugForm(str, Enum):
    """Hlavní lékové formy."""
    TABLET = "TBL"
    CAPSULE = "CPS"
    INJECTION = "INJ"
    CREAM = "CRM"
    OINTMENT = "UNG"
    SOLUTION = "SOL"
    SYRUP = "SIR"
    DROPS = "GTT"
    SUPPOSITORY = "SUP"
    PATCH = "EMP"
    SPRAY = "SPR"
    INHALATION = "INH"
    OTHER = "OTH"


# === Modely pro léčivé přípravky ===

class ActiveSubstance(BaseModel):
    """Účinná látka léčivého přípravku."""
    model_config = ConfigDict(extra="ignore")
    
    name: str = Field(..., description="Název účinné látky")
    name_en: Optional[str] = Field(None, description="Anglický název")
    strength: Optional[str] = Field(None, description="Síla (např. '500 mg')")
    unit: Optional[str] = Field(None, description="Jednotka dávkování")


class ATCGroup(BaseModel):
    """ATC klasifikační skupina."""
    model_config = ConfigDict(extra="ignore")
    
    code: str = Field(..., description="ATC kód (např. 'N02BE01')")
    name: str = Field(..., description="Název skupiny")
    level: int = Field(..., ge=1, le=5, description="Úroveň ATC (1-5)")


class MedicineSearchResult(BaseModel):
    """Výsledek vyhledávání léčivého přípravku."""
    model_config = ConfigDict(extra="ignore")
    
    sukl_code: str = Field(..., description="Kód SÚKL (7 číslic)")
    name: str = Field(..., description="Název přípravku")
    supplement: Optional[str] = Field(None, description="Doplněk názvu")
    strength: Optional[str] = Field(None, description="Síla přípravku")
    form: Optional[str] = Field(None, description="Léková forma")
    package: Optional[str] = Field(None, description="Velikost balení")
    atc_code: Optional[str] = Field(None, description="ATC kód")
    registration_status: Optional[str] = Field(None, description="Stav registrace")
    dispensation_mode: Optional[str] = Field(None, description="Režim výdeje")
    is_available: Optional[bool] = Field(None, description="Dostupnost na trhu")
    has_reimbursement: Optional[bool] = Field(None, description="Má úhradu")


class MedicineDetail(BaseModel):
    """Detailní informace o léčivém přípravku."""
    model_config = ConfigDict(extra="ignore")
    
    # Základní identifikace
    sukl_code: str = Field(..., description="Kód SÚKL")
    name: str = Field(..., description="Název přípravku")
    supplement: Optional[str] = Field(None, description="Doplněk názvu")
    
    # Složení a forma
    strength: Optional[str] = Field(None, description="Síla")
    form: Optional[str] = Field(None, description="Léková forma")
    route: Optional[str] = Field(None, description="Cesta podání")
    package_size: Optional[str] = Field(None, description="Velikost balení")
    package_type: Optional[str] = Field(None, description="Typ obalu")
    active_substances: list[ActiveSubstance] = Field(default_factory=list)
    
    # Registrace
    registration_number: Optional[str] = Field(None, description="Registrační číslo")
    registration_status: Optional[str] = Field(None, description="Stav registrace")
    registration_holder: Optional[str] = Field(None, description="Držitel rozhodnutí")
    registration_valid_until: Optional[date] = Field(None, description="Platnost do")
    
    # Klasifikace
    atc_code: Optional[str] = Field(None, description="ATC kód")
    atc_name: Optional[str] = Field(None, description="Název ATC skupiny")
    dispensation_mode: Optional[str] = Field(None, description="Režim výdeje")
    
    # Dostupnost
    is_available: Optional[bool] = Field(None, description="Aktuálně dostupný")
    is_marketed: Optional[bool] = Field(None, description="Uváděn na trh")
    unavailability_reason: Optional[str] = Field(None, description="Důvod nedostupnosti")
    
    # Úhrady
    has_reimbursement: Optional[bool] = Field(None, description="Hrazen pojišťovnou")
    max_price: Optional[float] = Field(None, description="Maximální cena")
    reimbursement_amount: Optional[float] = Field(None, description="Výše úhrady")
    patient_copay: Optional[float] = Field(None, description="Doplatek pacienta")
    
    # Dokumenty
    pil_available: bool = Field(False, description="Příbalový leták dostupný")
    spc_available: bool = Field(False, description="SPC dostupný")
    
    # Speciální příznaky
    is_narcotic: bool = Field(False, description="Omamná látka")
    is_psychotropic: bool = Field(False, description="Psychotropní látka")
    is_doping: bool = Field(False, description="Doping")
    is_biosimilar: bool = Field(False, description="Biosimilar")
    is_generic: bool = Field(False, description="Generikum")
    
    # Metadata
    last_updated: Optional[datetime] = Field(None, description="Poslední aktualizace")


# === Modely pro dokumenty ===

class PILContent(BaseModel):
    """Obsah příbalového letáku (PIL)."""
    model_config = ConfigDict(extra="ignore")
    
    sukl_code: str
    medicine_name: str
    document_code: Optional[str] = None
    
    # Sekce PIL
    what_is_and_what_for: Optional[str] = Field(None, alias="1_co_je_a_k_cemu")
    before_use: Optional[str] = Field(None, alias="2_nez_pouzijete")
    how_to_use: Optional[str] = Field(None, alias="3_jak_pouzivat")
    side_effects: Optional[str] = Field(None, alias="4_nezadouci_ucinky")
    storage: Optional[str] = Field(None, alias="5_uchovavani")
    other_info: Optional[str] = Field(None, alias="6_dalsi_informace")
    
    # Plný text
    full_text: Optional[str] = None
    
    # Metadata
    language: str = Field("cs", description="Jazyk dokumentu")
    document_url: Optional[str] = Field(None, description="URL PDF dokumentu")
    last_revision: Optional[date] = Field(None, description="Datum revize")


class SPCContent(BaseModel):
    """Obsah Souhrnu údajů o přípravku (SPC)."""
    model_config = ConfigDict(extra="ignore")
    
    sukl_code: str
    medicine_name: str
    document_code: Optional[str] = None
    
    # Klíčové sekce SPC
    name_and_form: Optional[str] = Field(None, description="1. Název a forma")
    composition: Optional[str] = Field(None, description="2. Složení")
    pharmaceutical_form: Optional[str] = Field(None, description="3. Léková forma")
    clinical_particulars: Optional[str] = Field(None, description="4. Klinické údaje")
    indications: Optional[str] = Field(None, description="4.1 Indikace")
    dosage: Optional[str] = Field(None, description="4.2 Dávkování")
    contraindications: Optional[str] = Field(None, description="4.3 Kontraindikace")
    warnings: Optional[str] = Field(None, description="4.4 Varování")
    interactions: Optional[str] = Field(None, description="4.5 Interakce")
    pregnancy: Optional[str] = Field(None, description="4.6 Těhotenství")
    side_effects: Optional[str] = Field(None, description="4.8 Nežádoucí účinky")
    overdose: Optional[str] = Field(None, description="4.9 Předávkování")
    
    full_text: Optional[str] = None
    document_url: Optional[str] = None
    last_revision: Optional[date] = None


# === Modely pro lékárny ===

class PharmacyInfo(BaseModel):
    """Informace o lékárně."""
    model_config = ConfigDict(extra="ignore")
    
    pharmacy_id: str = Field(..., description="ID lékárny")
    name: str = Field(..., description="Název lékárny")
    
    # Adresa
    street: Optional[str] = Field(None, description="Ulice a číslo")
    city: str = Field(..., description="Město")
    postal_code: Optional[str] = Field(None, description="PSČ")
    district: Optional[str] = Field(None, description="Okres")
    region: Optional[str] = Field(None, description="Kraj")
    
    # Kontakt
    phone: Optional[str] = Field(None, description="Telefon")
    email: Optional[str] = Field(None, description="E-mail")
    web: Optional[str] = Field(None, description="Web")
    
    # GPS
    latitude: Optional[float] = Field(None, description="Zeměpisná šířka")
    longitude: Optional[float] = Field(None, description="Zeměpisná délka")
    
    # Provoz
    operator: Optional[str] = Field(None, description="Provozovatel")
    pharmacy_type: Optional[str] = Field(None, description="Typ (základní/s rozšířenou)")
    
    # Služby
    has_24h_service: bool = Field(False, description="Nepřetržitý provoz")
    has_internet_sales: bool = Field(False, description="Internetový prodej")
    has_preparation_lab: bool = Field(False, description="Přípravna")
    
    # Stav
    is_active: bool = Field(True, description="Aktivní provoz")


# === Modely pro dostupnost a úhrady ===

class AvailabilityInfo(BaseModel):
    """Informace o dostupnosti léčivého přípravku."""
    model_config = ConfigDict(extra="ignore")
    
    sukl_code: str
    medicine_name: str
    
    is_available: bool = Field(..., description="Je dostupný")
    is_marketed: bool = Field(..., description="Je uváděn na trh")
    
    # Podrobnosti o nedostupnosti
    unavailability_type: Optional[str] = Field(None, description="Typ nedostupnosti")
    unavailability_reason: Optional[str] = Field(None, description="Důvod")
    unavailability_start: Optional[date] = Field(None, description="Od")
    unavailability_expected_end: Optional[date] = Field(None, description="Očekávaný konec")
    
    # Alternativy
    alternatives_available: bool = Field(False)
    alternative_sukl_codes: list[str] = Field(default_factory=list)
    
    # Statistiky
    last_delivery_date: Optional[date] = Field(None, description="Poslední dodávka")
    monthly_deliveries: Optional[int] = Field(None, description="Balení/měsíc")
    
    checked_at: datetime = Field(default_factory=datetime.now)


class ReimbursementInfo(BaseModel):
    """Informace o úhradě léčivého přípravku."""
    model_config = ConfigDict(extra="ignore")
    
    sukl_code: str
    medicine_name: str
    
    # Základní info
    is_reimbursed: bool = Field(..., description="Je hrazen")
    reimbursement_group: Optional[str] = Field(None, description="Úhradová skupina")
    
    # Ceny
    max_producer_price: Optional[float] = Field(None, description="Max. cena výrobce")
    max_retail_price: Optional[float] = Field(None, description="Max. cena v lékárně")
    reimbursement_amount: Optional[float] = Field(None, description="Výše úhrady")
    patient_copay: Optional[float] = Field(None, description="Doplatek pacienta")
    patient_copay_percent: Optional[float] = Field(None, description="Doplatek %")
    
    # Omezení
    has_indication_limit: bool = Field(False, description="Indikační omezení")
    indication_limit_text: Optional[str] = Field(None, description="Text omezení")
    has_quantity_limit: bool = Field(False, description="Množstevní limit")
    quantity_limit_text: Optional[str] = Field(None, description="Množstevní omezení")
    
    # Preskripce
    prescription_limit: Optional[str] = Field(None, description="Preskripční omezení")
    specialist_only: bool = Field(False, description="Pouze specialista")
    
    # Platnost
    valid_from: Optional[date] = Field(None)
    valid_until: Optional[date] = Field(None)


# === Modely pro interakce ===

class DrugInteraction(BaseModel):
    """Léková interakce."""
    model_config = ConfigDict(extra="ignore")
    
    drug_a_code: str
    drug_a_name: str
    drug_b_code: str
    drug_b_name: str
    
    severity: str = Field(..., description="Závažnost: low/medium/high/contraindicated")
    mechanism: Optional[str] = Field(None, description="Mechanismus interakce")
    clinical_effect: Optional[str] = Field(None, description="Klinický efekt")
    recommendation: Optional[str] = Field(None, description="Doporučení")
    
    evidence_level: Optional[str] = Field(None, description="Úroveň důkazů")
    source: Optional[str] = Field(None, description="Zdroj informace")


# === API Response modely ===

class SearchResponse(BaseModel):
    """Odpověď na vyhledávací dotaz."""
    query: str
    total_results: int
    page: int = 1
    page_size: int = 20
    results: list[MedicineSearchResult]
    search_time_ms: Optional[float] = None


class ErrorResponse(BaseModel):
    """Chybová odpověď."""
    error: str
    error_code: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
