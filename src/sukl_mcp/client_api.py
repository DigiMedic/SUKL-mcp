"""
REST API klient pro SÚKL portál prehledy.sukl.cz.

Poskytuje real-time přístup k SÚKL datům přes oficiální REST API.
Používá se jako doplněk k CSV klientovi pro aktuální data.
"""

import asyncio
import logging
from typing import Any, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field

from sukl_mcp.exceptions import SUKLDataError, SUKLValidationError

logger = logging.getLogger(__name__)


# =============================================================================
# API Configuration
# =============================================================================


class SUKLAPIConfig(BaseModel):
    """Konfigurace SÚKL REST API klientů."""

    # Base URLs pro jednotlivá API
    base_url_dlp: str = Field(
        default="https://prehledy.sukl.cz/dlp/v1",
        description="API pro léčivé přípravky (přehled léčiv)",
    )
    base_url_prehledy: str = Field(
        default="https://prehledy.sukl.cz/prehledy/openapi/v1",
        description="API pro lékárny a prodejce",
    )
    base_url_pd: str = Field(
        default="https://prehledy.sukl.cz/pd/openapi",
        description="API pro distributory",
    )
    base_url_hsz: str = Field(
        default="https://prehledy.sukl.cz/hsz/v1",
        description="API pro nedostupné LP (HSZ)",
    )
    base_url_vakciny: str = Field(
        default="https://prehledy.sukl.cz/vakciny",
        description="API pro šarže vakcín",
    )
    base_url_mr: str = Field(
        default="https://prehledy.sukl.cz/prehledy/v1",
        description="API pro market report",
    )

    # Timeouts
    connect_timeout: float = 10.0
    read_timeout: float = 30.0

    # Rate limiting
    requests_per_second: float = 5.0


# =============================================================================
# Response Models
# =============================================================================


class PharmacyAddress(BaseModel):
    """Adresa lékárny z API."""

    obec: str
    cast_obce: str | None = Field(None, alias="castObce")
    ulice: str | None = None
    cislo_popisne: str | None = Field(None, alias="cisloPopisne")
    cislo_orientacni: str | None = Field(None, alias="cisloOrientacni")
    psc: int | str
    kod_obce: str | None = Field(None, alias="kod_obce")
    kod_okresu: str | None = Field(None, alias="kod_okresu")
    nazev_okresu: str | None = Field(None, alias="nazev_okresu")

    model_config = ConfigDict(populate_by_name=True)  #


class PharmacyPerson(BaseModel):
    """Osoba (vedoucí lékárník) z API."""

    jmeno: str | None = None
    prijmeni: str | None = None
    titul_pred: str | None = Field(None, alias="titulPred")
    titul_za: str | None = Field(None, alias="titulZa")

    model_config = ConfigDict(populate_by_name=True)  #


class OpeningHoursPeriod(BaseModel):
    """Jedna časová perioda otevírací doby."""

    od: str
    do: str


class OpeningHoursDay(BaseModel):
    """Otevírací doba pro jeden den."""

    den: int  # 1=Po, 2=Út, ..., 7=Ne, 8=Svátek
    doby: list[OpeningHoursPeriod]
    poznamka: str | None = None


class OpeningHours(BaseModel):
    """Kompletní otevírací doba lékárny."""

    polozky: list[OpeningHoursDay]
    pohotovost: bool = False
    rozsirena_prac_doba: bool = Field(False, alias="rozsirenaPracDoba")

    model_config = ConfigDict(populate_by_name=True)  #


class PharmacyContacts(BaseModel):
    """Kontaktní údaje lékárny."""

    telefon: list[str | None] = Field(default_factory=list)
    email: list[str | None] = Field(default_factory=list)
    web: list[str | None] = Field(default_factory=list)
    fb: list[str | None] = Field(default_factory=list)
    twitter: list[str | None] = Field(default_factory=list)

    @property
    def telefon_clean(self) -> list[str]:
        """Vrátí seznam telefonů bez None hodnot."""
        return [t for t in self.telefon if t is not None]

    @property
    def email_clean(self) -> list[str]:
        """Vrátí seznam emailů bez None hodnot."""
        return [e for e in self.email if e is not None]

    @property
    def web_clean(self) -> list[str]:
        """Vrátí seznam webů bez None hodnot."""
        return [w for w in self.web if w is not None]


class PharmacyCoordinates(BaseModel):
    """GPS souřadnice lékárny."""

    gpsn: float | None = None  # Zeměpisná šířka
    gpse: float | None = None  # Zeměpisná délka


class PharmacyAPIResponse(BaseModel):
    """Lékárna vrácená z API."""

    nazev: str | None = None
    kod_pracoviste: str | None = Field(None, alias="kodPracoviste")
    kod_lekarny: str | None = Field(None, alias="kodLekarny")
    icz: str | None = None
    ico: str | None = None
    typ_lekarny: str | None = Field(None, alias="typLekarny")
    adresa: PharmacyAddress | None = None
    vedouci_lekarnik: PharmacyPerson | None = Field(None, alias="vedouciLekarnik")
    kontakty: PharmacyContacts | None = None
    oteviraci_doba: OpeningHours | None = Field(None, alias="oteviraciDoba")
    eshop: list[str | None] | None = Field(default=None)
    souradnice: PharmacyCoordinates | None = None

    model_config = ConfigDict(populate_by_name=True)  #


class MedicineAPIDetail(BaseModel):
    """Detail léčivého přípravku z DLP API."""

    kod_sukl: str = Field(alias="kodSukl")
    nazev: str
    doplnek: str | None = None
    sila: str | None = None
    forma: str | None = None
    baleni: str | None = None
    cesta: str | None = None
    atc_kod: str | None = Field(None, alias="ATCkod")
    registracni_cislo: str | None = Field(None, alias="registracniCislo")
    drzitel: str | None = None
    zemeDrzitele: str | None = None
    je_dodavka: bool | None = Field(None, alias="jeDodavka")
    vydej_kod: str | None = Field(None, alias="zpusobVydejeKod")
    vydej_text: str | None = Field(None, alias="zpusobVydejeText")
    omamne: bool = False
    psychotropni: bool = False
    doping: bool = False

    model_config = ConfigDict(populate_by_name=True)  #


class PriceReimbursementAPI(BaseModel):
    """Cenové a úhradové informace z API /cau-scau."""

    kod_sukl: str = Field(alias="kodSukl")
    nazev: str | None = None
    doplnek: str | None = None
    cena_puvodce: float | None = Field(None, alias="cenaPuvodce")
    cena_velkoobchod: float | None = Field(None, alias="maxCenaVelkoobchod")
    cena_lekarna: float | None = Field(None, alias="maxCenaLekarna")
    uhrady: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)  #


class UnavailableMedicine(BaseModel):
    """Nedostupný léčivý přípravek z HSZ API."""

    id_pozadavku: str = Field(alias="idPozadavku")
    kod_sukl: str = Field(alias="kodSUKL")
    nazev: str
    doplnek: str | None = None
    typ: int  # 1=JR, 2=OOP
    periodicita: int | None = None
    skupina_hlasitelu: list[str] | None = Field(None, alias="skupinaHlasitelu")
    plat_od: str | None = Field(None, alias="platOd")
    plat_do: str | None = Field(None, alias="platDo")

    model_config = ConfigDict(populate_by_name=True)  #


class MarketReportEntry(BaseModel):
    """Záznam z market reportu."""

    id: int
    kod_sukl: str = Field(alias="kodSUKL")
    typ_oznameni: str = Field(alias="typOznameni")  # zahajeni/preruseni/obnoveni/ukonceni
    plat_od: str = Field(alias="platOd")
    nahrazujici_lp: list[str] | None = Field(None, alias="nahrazujiciLP")
    termin_obnovy: str | None = Field(None, alias="terminObnovy")
    duvod_preruseni: str | None = Field(None, alias="duvodPreruseni")
    datum_hlaseni: str = Field(alias="datumHlaseni")
    poznamka: str | None = None

    model_config = ConfigDict(populate_by_name=True)  #


class VaccineBatch(BaseModel):
    """Šarže vakcíny."""

    kod_sukl: str = Field(alias="kodSUKL")
    nazev: str | None = None
    sarze: str
    propusteno_dne: str | None = Field(None, alias="propustenoDne")
    expirace: str | None = None

    model_config = ConfigDict(populate_by_name=True)  #


class DistributorAddress(BaseModel):
    """Adresa distributora."""

    psc: str | None = None
    ulice: str | None = None
    cislo_popisne: str | None = Field(None, alias="cisloPopisne")
    cislo_orientacni: str | None = Field(None, alias="cisloOrientacni")
    stat: str | None = None

    model_config = ConfigDict(populate_by_name=True)  #


class DistributorSidlo(BaseModel):
    """Sídlo distributora."""

    ico: str | None = None
    nazev: str | None = None
    adresa: DistributorAddress | None = None
    povoleni_vydeje: bool = Field(False, alias="povoleni_vydeje")
    povoleni_sukl: bool = Field(False, alias="povoleni_sukl")
    povoleni_eu: bool = Field(False, alias="povoleni_eu")

    model_config = ConfigDict(populate_by_name=True)  #


class DistributorPerson(BaseModel):
    """Osoba v distribuční firmě."""

    jmeno: str | None = None
    tel: list[str | None] = Field(default_factory=list)
    email: list[str | None] = Field(default_factory=list)
    web: list[str | None] = Field(default_factory=list)
    mobil: list[str | None] = Field(default_factory=list)
    ds: list[str | None] = Field(default_factory=list)


class DistributorAPIResponse(BaseModel):
    """Distributor z API."""

    typ: str | None = None
    kod_pracoviste: str | None = Field(None, alias="kodPracoviste")
    nazev: str | None = None
    adresa: DistributorAddress | None = None
    sidlo: DistributorSidlo | None = None
    kontakty: dict[str, Any] | None = None
    osoby: list[DistributorPerson] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)  #

    @property
    def ico(self) -> str | None:
        """Vrátí IČO ze sídla."""
        return self.sidlo.ico if self.sidlo else None


# =============================================================================
# API Client
# =============================================================================


class SUKLAPIClient:
    """
    REST API klient pro SÚKL portál.

    Poskytuje přístup k následujícím API:
    - /dlp/v1 - Léčivé přípravky (detail, ceny, složení, dokumenty)
    - /prehledy/openapi/v1 - Lékárny, prodejci vyhrazených léčiv
    - /pd/openapi - Distributoři
    - /hsz/v1 - Nedostupné léčivé přípravky
    - /vakciny - Šarže vakcín
    - /prehledy/v1 - Market report
    """

    _instance: "SUKLAPIClient | None" = None
    _lock = asyncio.Lock()

    def __init__(self, config: SUKLAPIConfig | None = None):
        self.config = config or SUKLAPIConfig()
        self._client: httpx.AsyncClient | None = None
        self._last_request_time: float = 0.0

    @classmethod
    async def get_instance(cls) -> "SUKLAPIClient":
        """Thread-safe singleton přístup."""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization HTTP klienta."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=self.config.connect_timeout,
                    read=self.config.read_timeout,
                    write=30.0,
                    pool=30.0,
                ),
                follow_redirects=True,
            )
        return self._client

    async def _rate_limit(self) -> None:
        """Jednoduchý rate limiter."""
        import time

        min_interval = 1.0 / self.config.requests_per_second
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Vykoná HTTP request s rate limitingem."""
        await self._rate_limit()
        client = await self._get_client()

        try:
            response = await client.request(method, url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {url}")
            raise SUKLDataError(f"API chyba: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Request error: {url} - {e}")
            raise SUKLDataError(f"Chyba připojení k API: {e}") from e

    async def close(self) -> None:
        """Uzavře HTTP klienta."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # Lékárny API (/prehledy/openapi/v1/lekarny)
    # =========================================================================

    async def get_all_pharmacies(
        self,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[PharmacyAPIResponse], int]:
        """
        Získá seznam lékáren s paginací.

        Args:
            page: Číslo stránky (od 1)
            page_size: Počet záznamů na stránku (max 1000)

        Returns:
            Tuple (seznam lékáren, celkový počet)
        """
        url = f"{self.config.base_url_prehledy}/lekarny"
        params = {"stranka": page, "pocet": min(page_size, 1000)}

        data = await self._request("GET", url, params)
        pharmacies = [PharmacyAPIResponse.model_validate(p) for p in data.get("data", [])]
        total = data.get("celkem", len(pharmacies))

        return pharmacies, total

    async def get_pharmacy_by_code(self, code: str) -> PharmacyAPIResponse | None:
        """
        Získá detail lékárny podle kódu pracoviště.

        Args:
            code: Kód pracoviště (11 číslic)

        Returns:
            Detail lékárny nebo None
        """
        url = f"{self.config.base_url_prehledy}/lekarny/{code}"
        try:
            data = await self._request("GET", url)
            return PharmacyAPIResponse.model_validate(data)
        except SUKLDataError:
            return None

    async def search_pharmacies_by_city(
        self,
        city: str,
        limit: int = 50,
    ) -> list[PharmacyAPIResponse]:
        """
        Vyhledá lékárny v daném městě.

        Poznámka: API nepodporuje filtrování, musíme stáhnout vše a filtrovat lokálně.

        Args:
            city: Název města
            limit: Maximální počet výsledků

        Returns:
            Seznam lékáren
        """
        all_pharmacies = []
        page = 1
        page_size = 500
        city_lower = city.lower()

        while True:
            pharmacies, total = await self.get_all_pharmacies(page, page_size)
            if not pharmacies:
                break

            for p in pharmacies:
                # Null-safe přístup k adrese
                if p.adresa and p.adresa.obec and city_lower in p.adresa.obec.lower():
                    all_pharmacies.append(p)
                    if len(all_pharmacies) >= limit:
                        return all_pharmacies

            if page * page_size >= total:
                break
            page += 1

        return all_pharmacies[:limit]

    # =========================================================================
    # Léčivé přípravky API (/dlp/v1)
    # =========================================================================

    async def get_medicine_detail(self, sukl_code: str) -> MedicineAPIDetail | None:
        """
        Získá detail léčivého přípravku podle SÚKL kódu.

        Args:
            sukl_code: 7místný SÚKL kód

        Returns:
            Detail léčiva nebo None
        """
        # Validace kódu
        if not sukl_code or len(sukl_code) != 7 or not sukl_code.isdigit():
            raise SUKLValidationError(f"Neplatný SÚKL kód: {sukl_code}")

        url = f"{self.config.base_url_dlp}/lecive-pripravky/{sukl_code}"
        try:
            data = await self._request("GET", url)
            return MedicineAPIDetail.model_validate(data)
        except SUKLDataError:
            return None

    async def get_price_reimbursement(self, sukl_code: str) -> PriceReimbursementAPI | None:
        """
        Získá cenové a úhradové informace pro léčivý přípravek.

        Args:
            sukl_code: 7místný SÚKL kód

        Returns:
            Cenové informace nebo None (pokud LP nemá stanovenou úhradu)
        """
        if not sukl_code or len(sukl_code) != 7 or not sukl_code.isdigit():
            raise SUKLValidationError(f"Neplatný SÚKL kód: {sukl_code}")

        url = f"{self.config.base_url_dlp}/cau-scau/{sukl_code}"
        try:
            data = await self._request("GET", url)
            return PriceReimbursementAPI.model_validate(data)
        except SUKLDataError:
            return None

    async def get_medicine_composition(self, sukl_code: str) -> list[dict[str, Any]]:
        """
        Získá složení léčivého přípravku.

        Args:
            sukl_code: 7místný SÚKL kód

        Returns:
            Seznam složek
        """
        if not sukl_code or len(sukl_code) != 7 or not sukl_code.isdigit():
            raise SUKLValidationError(f"Neplatný SÚKL kód: {sukl_code}")

        url = f"{self.config.base_url_dlp}/slozeni/{sukl_code}"
        try:
            result = await self._request("GET", url)
            return cast(list[dict[str, Any]], result)
        except SUKLDataError:
            return []

    async def get_document_metadata(self, sukl_code: str) -> dict[str, Any] | None:
        """
        Získá metadata dokumentů (PIL, SPC, obal) pro léčivý přípravek.

        Args:
            sukl_code: 7místný SÚKL kód

        Returns:
            Metadata dokumentů
        """
        if not sukl_code or len(sukl_code) != 7 or not sukl_code.isdigit():
            raise SUKLValidationError(f"Neplatný SÚKL kód: {sukl_code}")

        url = f"{self.config.base_url_dlp}/dokumenty-metadata/{sukl_code}"
        try:
            result = await self._request("GET", url)
            return cast(dict[str, Any], result)
        except SUKLDataError:
            return None

    async def get_document_url(self, sukl_code: str, doc_type: str) -> str | None:
        """
        Získá URL dokumentu (PIL, SPC, obal).

        Args:
            sukl_code: 7místný SÚKL kód
            doc_type: Typ dokumentu ('pil', 'spc', 'obal')

        Returns:
            URL dokumentu nebo None
        """
        metadata = await self.get_document_metadata(sukl_code)
        if not metadata:
            return None

        doc_type_lower = doc_type.lower()
        doc_id = None

        if doc_type_lower == "pil" and "pil" in metadata:
            doc_id = metadata["pil"].get("id")
        elif doc_type_lower == "spc" and "spc" in metadata:
            doc_id = metadata["spc"].get("id")
        elif doc_type_lower == "obal" and "obal" in metadata:
            doc_id = metadata["obal"].get("id")

        if doc_id:
            return f"{self.config.base_url_dlp}/dokumenty/{doc_id}"
        return None

    # =========================================================================
    # Nedostupné LP API (/hsz/v1)
    # =========================================================================

    async def get_unavailable_medicines(
        self,
        type_filter: int | None = None,
    ) -> list[UnavailableMedicine]:
        """
        Získá seznam nedostupných léčivých přípravků.

        Args:
            type_filter: 1=JR (jednorázový požadavek), 2=OOP (omezená dostupnost)

        Returns:
            Seznam nedostupných LP
        """
        url = f"{self.config.base_url_hsz}/nedostupne-lp"
        params = {}
        if type_filter:
            params["typ"] = type_filter

        data = await self._request("GET", url, params)
        return [UnavailableMedicine.model_validate(m) for m in data]

    async def is_medicine_unavailable(self, sukl_code: str) -> bool:
        """
        Zkontroluje, zda je léčivý přípravek v seznamu nedostupných.

        Args:
            sukl_code: 7místný SÚKL kód

        Returns:
            True pokud je LP nedostupný
        """
        unavailable = await self.get_unavailable_medicines()
        return any(m.kod_sukl == sukl_code for m in unavailable)

    # =========================================================================
    # Market Report API (/prehledy/v1/marketreport)
    # =========================================================================

    async def get_market_report(self) -> list[MarketReportEntry]:
        """
        Získá kompletní market report (hlášení o uvádění LP na trh).

        Returns:
            Seznam hlášení
        """
        url = f"{self.config.base_url_mr}/marketreport/posledni-hlaseni"
        data = await self._request("GET", url)
        return [MarketReportEntry.model_validate(m) for m in data.get("data", [])]

    async def get_market_report_for_medicine(self, sukl_code: str) -> MarketReportEntry | None:
        """
        Získá market report pro konkrétní léčivý přípravek.

        Args:
            sukl_code: 7místný SÚKL kód

        Returns:
            Poslední hlášení nebo None
        """
        if not sukl_code or len(sukl_code) != 7 or not sukl_code.isdigit():
            raise SUKLValidationError(f"Neplatný SÚKL kód: {sukl_code}")

        url = f"{self.config.base_url_mr}/marketreport/posledni-hlaseni/{sukl_code}"
        try:
            data = await self._request("GET", url)
            return MarketReportEntry.model_validate(data)
        except SUKLDataError:
            return None

    async def get_last_market_change(self) -> dict[str, Any]:
        """
        Získá informaci o poslední změně v market reportu.

        Returns:
            Dict s kodSUKL a casHlaseni
        """
        url = f"{self.config.base_url_mr}/marketreport/posledni-zmena"
        result = await self._request("GET", url)
        return cast(dict[str, Any], result)

    # =========================================================================
    # Šarže vakcín API (/vakciny)
    # =========================================================================

    async def get_vaccine_batches(
        self, sukl_code: str | None = None
    ) -> tuple[list[VaccineBatch], str | None]:
        """
        Získá seznam propuštěných šarží vakcín.

        Args:
            sukl_code: Volitelný filtr podle SÚKL kódu

        Returns:
            Tuple (seznam šarží, datum poslední změny)
        """
        if sukl_code:
            url = f"{self.config.base_url_vakciny}/sarze/{sukl_code}"
        else:
            url = f"{self.config.base_url_vakciny}/sarze"

        data = await self._request("GET", url)
        batches = [VaccineBatch.model_validate(b) for b in data.get("data", [])]
        last_change = data.get("posledniZmena")

        return batches, last_change

    # =========================================================================
    # Distributoři API (/pd/openapi)
    # =========================================================================

    async def get_all_distributors(self) -> list[DistributorAPIResponse]:
        """
        Získá seznam všech distributorů léčiv.

        Returns:
            Seznam distributorů
        """
        url = f"{self.config.base_url_pd}/distributori"
        data = await self._request("GET", url)
        # API může vracet dict s "data" klíčem nebo přímo seznam
        if isinstance(data, dict):
            items = data.get("data", [])
        else:
            items = data
        return [DistributorAPIResponse.model_validate(d) for d in items if isinstance(d, dict)]

    async def get_distributor_by_code(self, code: str) -> DistributorAPIResponse | None:
        """
        Získá detail distributora podle kódu pracoviště.

        Args:
            code: Kód pracoviště (11 číslic)

        Returns:
            Detail distributora nebo None
        """
        url = f"{self.config.base_url_pd}/distributor/{code}"
        try:
            data = await self._request("GET", url)
            return DistributorAPIResponse.model_validate(data)
        except SUKLDataError:
            return None

    # =========================================================================
    # Prodejci vyhrazených léčiv API (/prehledy/openapi/v1/prodejci)
    # =========================================================================

    async def get_all_sellers(self) -> tuple[list[dict[str, Any]], int]:
        """
        Získá seznam všech prodejců vyhrazených léčiv.

        Returns:
            Tuple (seznam prodejců, celkový počet)
        """
        url = f"{self.config.base_url_prehledy}/prodejci"
        data = await self._request("GET", url)
        return data.get("data", []), data.get("celkem", 0)

    # =========================================================================
    # Číselníky API (/dlp/v1/ciselniky)
    # =========================================================================

    async def get_atc_codes(self) -> list[dict[str, Any]]:
        """
        Získá kompletní číselník ATC skupin.

        Returns:
            Seznam ATC kódů s názvy
        """
        url = f"{self.config.base_url_dlp}/ciselniky/atc-skupiny"
        result = await self._request("GET", url)
        return cast(list[dict[str, Any]], result)

    async def get_substances(self) -> list[dict[str, Any]]:
        """
        Získá číselník látek.

        Returns:
            Seznam látek
        """
        url = f"{self.config.base_url_dlp}/ciselnik-latky"
        result = await self._request("GET", url)
        return cast(list[dict[str, Any]], result)

    async def get_dispensation_modes(self) -> list[dict[str, Any]]:
        """
        Získá číselník způsobů výdeje.

        Returns:
            Seznam způsobů výdeje
        """
        url = f"{self.config.base_url_dlp}/ciselniky/zpusob-vydeje"
        result = await self._request("GET", url)
        return cast(list[dict[str, Any]], result)

    # =========================================================================
    # Status API
    # =========================================================================

    async def check_api_status(self) -> dict[str, bool]:
        """
        Zkontroluje dostupnost všech API endpointů.

        Returns:
            Dict s názvy API a jejich statusem
        """
        results = {}

        # DLP API
        try:
            await self._request("GET", f"{self.config.base_url_dlp}/status")
            results["dlp"] = True
        except Exception:
            results["dlp"] = False

        # Prehledy API (lékárny)
        try:
            await self._request(
                "GET", f"{self.config.base_url_prehledy.replace('/openapi/v1', '')}/status"
            )
            results["prehledy"] = True
        except Exception:
            results["prehledy"] = False

        return results


# =============================================================================
# Helper Functions
# =============================================================================


def pharmacy_api_to_info(pharmacy: PharmacyAPIResponse) -> dict[str, Any]:
    """
    Konvertuje PharmacyAPIResponse na formát kompatibilní s PharmacyInfo.

    Args:
        pharmacy: Lékárna z API

    Returns:
        Dict kompatibilní s PharmacyInfo modelem
    """
    addr = pharmacy.adresa

    # Sestavení ulice s číslem (null-safe)
    street_parts = []
    if addr and addr.ulice:
        street_parts.append(addr.ulice)
    if addr and addr.cislo_popisne:
        street_parts.append(addr.cislo_popisne)
    if addr and addr.cislo_orientacni:
        street_parts.append(f"/{addr.cislo_orientacni}")
    street = " ".join(street_parts) if street_parts else None

    # Kontakty (null-safe)
    contacts = pharmacy.kontakty
    phone = contacts.telefon[0] if contacts and contacts.telefon else None
    email = contacts.email[0] if contacts and contacts.email else None
    web = contacts.web[0] if contacts and contacts.web else None

    # GPS
    lat = pharmacy.souradnice.gpsn if pharmacy.souradnice else None
    lon = pharmacy.souradnice.gpse if pharmacy.souradnice else None

    # Otevírací doba - kontrola 24h služby (null-safe)
    has_24h = pharmacy.oteviraci_doba.pohotovost if pharmacy.oteviraci_doba else False

    return {
        "pharmacy_id": pharmacy.kod_pracoviste,
        "name": pharmacy.nazev,
        "street": street,
        "city": addr.obec if addr else None,
        "postal_code": str(addr.psc) if addr and addr.psc else None,
        "district": addr.nazev_okresu if addr else None,
        "region": None,  # API neposkytuje kraj
        "phone": phone,
        "email": email,
        "web": web,
        "latitude": lat,
        "longitude": lon,
        "operator": None,  # API neposkytuje provozovatele přímo
        "has_24h_service": has_24h,
        "has_internet_sales": bool(pharmacy.eshop),
        "has_preparation_lab": False,  # API neposkytuje
        "is_active": True,
    }
