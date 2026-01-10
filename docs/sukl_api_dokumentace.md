# SÚKL API Dokumentace

## Základní informace

**Base URL**: `https://prehledy.sukl.cz/prehledy/v1`
**Formát dat**: JSON
**Metoda autentizace**: Neprovádí se (veřejné API)

## Hlavičky požadavků

Doporučené hlavičky pro přístup k API:

```http
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
Accept: application/json, text/plain, */*
Content-Type: application/json
Referer: https://prehledy.sukl.cz/
```

## API Endpointy

### 1. POST /dlprc - Seznam léčivých přípravků (REGISTERED)

Hlavní endpoint pro získání seznamu registrovaných léčivých přípravků. Tento endpoint NENÍ zdokumentován v oficiálním OpenAPI specifikaci.

**URL**: `POST https://prehledy.sukl.cz/prehledy/v1/dlprc`

#### Parametry těla požadavku (JSON)

```json
{
  "atc": "string",           // Volitelné - ATC kód (např. "A10AE04")
  "stavRegistrace": "string",  // Volitelné - Stav registrace (R, N, Z, atd.)
  "uhrada": "string",        // Volitelné - Kód úhrady (A, B, D, atd.)
  "jeDodavka": boolean,       // Volitelné - Pouze přípravky s aktivním výskytem na trhu (true/false)
  "jeRegulovany": boolean,    // Volitelné - Pouze regulované přípravky (true/false)
  "stranka": number,          // Volitelné - Číslo stránky (default: 1)
  "pocet": number            // Volitelné - Počet záznamů na stránku (default: 10)
}
```

#### Příklad požadavku

```bash
curl -X POST "https://prehledy.sukl.cz/prehledy/v1/dlprc" \
  -H "Content-Type: application/json" \
  -d '{"atc":"A10AE04","stranka":1,"pocet":5}'
```

#### Odpověď

```json
{
  "data": [
    {
      "registracniCisloDisplay": "EU/1/14/944/008",
      "registracniCislo": "EU/1/14/944/008",
      "kodSUKL": "0209084",
      "nazevLP": "ABASAGLAR",
      "doplnekNazvu": "100U/ML INJ SOL 1X3ML PEN",
      "sila": "100U/ML",
      "lekovaForma": {
        "kod": "INJ SOL",
        "nazev": {
          "cs": "Injekční roztok",
          "en": "Solution for injection"
        }
      },
      "cestaPodani": {
        "kod": "SDR",
        "nazev": {
          "cs": "Subkutánní podání",
          "en": "Subcutaneous use"
        }
      },
      "stavRegistrace": "R",
      "jeRegulovany": false,
      "jeDodavka": true,
      "uhrada": "A",
      "dovoz": "",
      "dostupnost": "D",
      "atc": {
        "kod": "A10AE04",
        "nazev": {
          "cs": "INSULIN GLARGIN",
          "en": "INSULIN GLARGINE"
        }
      },
      "zpusobVydeje": "R"
    }
  ],
  "celkem": 58,
  "extraSearch": []
}
```

#### Vysvětlení polí

- `jeDodavka`: Pouze přípravky s aktivním výskytem na trhu (true/false)
- `jeRegulovany`: Je regulovaný (true/false)
- `registracniCisloDisplay`: Registrační číslo pro zobrazení
- `registracniCislo`: Registrační číslo
- `kodSUKL`: Kód SÚKL (jedinečný identifikátor)
- `nazevLP`: Název léčivého přípravku
- `doplnekNazvu`: Doplněk názvu (síla, forma, balení)
- `sila`: Síla přípravku
- `lekovaForma`: Léková forma (s kódem a názvem v češtině a angličtině)
- `cestaPodani`: Cesta podání (s kódem a názvem v češtině a angličtině)
- `stavRegistrace`: Stav registrace (R - registrovaný, N - neregistrovaný, atd.)
- `jeRegulovany`: Je regulovaný (true/false)
- `jeDodavka`: Je v aktivním výskytu na trhu (true/false)
- `uhrada`: Kód úhrady (A, B, C, nebo null)
- `dovoz`: Dovoz (prázdný string nebo kód)
- `dostupnost`: Dostupnost (D - dostupný, nebo null)
- `atc`: ATC kódifikace (kód a název v češtině a angličtině)
- `zpusobVydeje`: Způsob výdeje (R - na recept)
- `celkem`: Celkový počet záznamů
- `extraSearch`: Další možnosti vyhledávání (pole)

---

### 2. GET /lekarny - Seznam lékáren

Získá seznam lékáren s možností stránkování.

**URL**: `GET https://prehledy.sukl.cz/prehledy/v1/lekarny`

#### Query parametry

- `stranka` (number) - Číslo stránky (default: 1)
- `pocet` (number) - Počet záznamů na stránku

#### Příklad požadavku

```bash
curl "https://prehledy.sukl.cz/prehledy/v1/lekarny?stranka=1&pocet=5"
```

#### Odpověď

```json
{
  "data": [
    {
      "nazev": "Horská lékárna s.r.o.",
      "kodPracoviste": "67350000000",
      "kodLekarny": "67995050",
      "icz": "67350000",
      "ico": "28803965",
      "typLekarny": "Lékárna",
      "adresa": {
        "obec": "Rokytnice nad Jizerou",
        "castObce": "Horní Rokytnice",
        "ulice": "Horní Rokytnice",
        "cisloPopisne": "275",
        "cisloOrientacni": "",
        "psc": "51244",
        "kod_obce": "577456",
        "kod_okresu": "3608",
        "nazev_okresu": "Semily"
      },
      "vedouciLekarnik": {
        "jmeno": "Jitka",
        "prijmeni": "Boudová",
        "titulPred": "Mgr.",
        "titulZa": ""
      },
      "kontakty": {
        "telefon": ["481 523 442"],
        "email": [],
        "web": []
      },
      "geo": {
        "lat": 50.626789,
        "lon": 15.419878
      },
      "oteviraciDoba": [
        {
          "den": "Pondělí",
          "od": "8:00",
          "do": "17:00"
        }
      ]
    }
  ],
  "celkem": 4896
}
```

---

### 3. GET /lekarny/{kod} - Detail lékárny

Získá detailní informace o lékárně podle jejího kódu.

**URL**: `GET https://prehledy.sukl.cz/prehledy/v1/lekarny/{kod}`

#### Příklad požadavku

```bash
curl "https://prehledy.sukl.cz/prehledy/v1/lekarny/67995050"
```

---

### 4. GET /ciselniky/{nazev} - Číselníky

Získá hodnoty z konkrétního číselníku.

**Dostupné číselníky**:
- `cesty_podani` - Cesty podání léků
- `stavy_registrace` - Stavy registrace
- `vydeje` - Způsoby výdeje
- `brailovo_pismo` - Braillovo písmo
- `uhrady` - Úhrady
- `dovozy` - Dovozy
- `dostupnosti` - Dostupnosti
- `stavy_zruseni` - Stavy zrušení
- `ostatni` - Ostatní
- `ochranne_prvky` - Ochranné prvky

#### Příklad požadavku

```bash
curl "https://prehledy.sukl.cz/prehledy/v1/ciselniky/cesty_podani"
```

#### Odpověď

```json
[
  {
    "kod": "POR",
    "nazev": "Perorální podání"
  },
  {
    "kod": "IVN",
    "nazev": "Intravenózní podání"
  }
]
```

---

### 5. GET /ciselniky/latky - ATC kód léčivých látek

Získá seznam ATC kódů a názvů léčivých látek.

**URL**: `GET https://prehledy.sukl.cz/prehledy/v1/ciselniky/latky`

#### Příklad požadavku

```bash
curl "https://prehledy.sukl.cz/prehledy/v1/ciselniky/latky"
```

#### Odpověď

```json
[
  {
    "kod": "A07EC01",
    "nazev": "SULFASALAZIN"
  },
  {
    "kod": "A02BC01",
    "nazev": "CIMETIDIN"
  }
]
```

---

### 6. GET /datum-aktualizace - Datum aktualizace dat

Získá datum poslední aktualizace dat v databázi.

**URL**: `GET https://prehledy.sukl.cz/prehledy/v1/datum-aktualizace`

#### Příklad požadavku

```bash
curl "https://prehledy.sukl.cz/prehledy/v1/datum-aktualizace"
```

#### Odpověď

```json
{
  "DLPO": "2025-12-01 00:00:00",
  "DLPW": "2026-01-05 23:00:00",
  "SCAU": "2026-01-01 00:00:00"
}
```

#### Vysvětlení polí

- `DLPO`: Datum aktualizace léčivých přípravků
- `DLPW`: Datum aktualizace skladových zásob
- `SCAU`: Datum aktualizace cen a úhrad

---

## Nedokumentované nebo nefunkční endpointy

Následující endpointy jsou uvedeny v oficiálním OpenAPI specifikaci, ale:

1. **GET /dlp** - Vrací prázdnou odpověď nebo HTTP 504
2. **GET /lecive-pripravky** - Vrací prázdnou odpověď nebo HTTP 504
3. **GET /lecive-pripravky/{kodSukl}** - Vrací prázdnou odpověď
4. **GET /cau-scau/{kodSukl}** - Vrací prázdnou odpověď (ceny a úhrady)
5. **GET /cau-scup/{kodSukl}** - Vrací prázdnou odpověď (nouzová péče)
6. **GET /cau-sneh/{kodSukl}** - Vrací prázdnou odpověď (nehraditelné)
7. **GET /slozeni/{kodSukl}** - Vrací prázdnou odpověď (složení)
8. **GET /dokumenty-metadata/{kodSukl}** - Vrací prázdnou odpověď
9. **POST /dle** - Tento endpoint je zmíněn v UI, ale není definován v OpenAPI

**Důvod**: Tyto endpointy mohou vyžadovat:
- Specifické hlavičky nebo cookies
- Další autentizační prvky
- Jsou určeny pouze pro interní použití
- Mají dočasný výpadek

Doporučuje se použít **POST /dlprc** pro získání seznamu léků a případně kontaktovat SÚKL pro přístup k dalším detailům.

## Stavy registrace

- **R** - Registrovaný léčivý přípravek
- **B** - Přípravek po provedené změně může být uváděn na trh po dobu 6 měsíců a používán do uplynutí doby použitelnosti, nejdéle po dobu platnosti registrace
- **C** - Zrušená registrace, přípravek bude stažen z oběhu do doby uvedené v rozhodnutí o zrušení registrace
- **F** - Specifický léčebný program povolený MZČR na základě doporučení SÚKL
- **I** - Léčivý přípravek povolený na základě mimořádného opatření MZ
- **K** - Pozastavení rozhodnutí o centralizované registraci
- **M** - Pozastavení registrace nebo používání léčivého přípravku a jeho uvádění do oběhu
- **N** - Registrace zrušena rozhodnutím nebo uplynutím doby použitelnosti po provedené změně
- **Y** - Registrace, která pozbyla platnost, přípravek bude stažen z oběhu do doby uvedené v rozhodnutí
- **Z** - Registrace, která pozbyla platnost - nebyla prodloužena anebo bylo prodloužení zamítnuto
- **ZS** - Registrace zrušena na základě SUNSET

## Kódy úhrad

- **A** - Hrazený
- **B** - Plně hrazený
- **D** - Nehrazený
- **Další kódy** - Ostatní kódy úhrad (nutno ověřit v číselníku úhrad)

## Dostupnost

- **D** - Dostupný (aktivní výskyt na trhu)
- `null` - Nedostupný nebo neznámý

## Tip pro vývojáře

Pro automatické načítání dat je určeno API, nikoliv extrakce dat z GUI aplikace.

Více informací:
- Oficiální API dokumentace: https://prehledy.sukl.cz/docs/?url=/dlp.api.json#/
- Návod k API rozhraní: https://prehledy.sukl.cz/documents/PL-api-navod.pdf
- Technická podpora: kc.sukl.cz
