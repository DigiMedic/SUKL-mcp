# SUKL MCP Server — Architektura

## Prehled systemu

```mermaid
graph TB
    subgraph "Klienti"
        Claude["Claude / AI agent"]
        Cursor["Cursor / IDE"]
        Custom["Vlastni integrace"]
        Browser["Webovy prohlizec"]
    end

    subgraph "Vercel (fra1)"
        subgraph "Next.js 16 App"
            Landing["Landing Page<br/>src/app/page.tsx<br/>(12 sekci, SSG)"]
            MCP["MCP Endpoint<br/>POST /api/mcp<br/>(JSON-RPC 2.0)"]
            Demo["Demo API<br/>POST /api/demo<br/>(pattern matching)"]
        end

        subgraph "Business Logic"
            MCPHandler["mcp-handler.ts<br/>(9 nastroju)"]
            DemoHandler["demo-handler.ts<br/>(intent parser)"]
        end

        subgraph "Data Layer"
            Client["sukl-client.ts<br/>(server-only)"]
            Fuse["Fuse.js Index<br/>(fuzzy search)"]
            Store["In-Memory Store<br/>(medicines, pharmacies,<br/>reimbursements, ATC)"]
        end

        Data["bundled-data.json<br/>(10.4 MB)"]
    end

    SUKL["SUKL API<br/>prehledy.sukl.cz<br/>(PIL/SPC dokumenty)"]

    Claude -->|JSON-RPC| MCP
    Cursor -->|JSON-RPC| MCP
    Custom -->|JSON-RPC| MCP
    Browser -->|HTTP| Landing
    Browser -->|POST| Demo

    MCP --> MCPHandler
    Demo --> DemoHandler
    MCPHandler --> Client
    DemoHandler --> Client
    Client --> Fuse
    Client --> Store
    Store ---|fs.readFileSync| Data
    Client -.->|on-demand fetch| SUKL
```

---

## Datovy tok

```mermaid
sequenceDiagram
    participant C as MCP Client
    participant R as route.ts
    participant H as mcp-handler.ts
    participant S as sukl-client.ts
    participant D as bundled-data.json
    participant A as SUKL API

    C->>R: POST /mcp (JSON-RPC)
    R->>R: Rate limit check (100/min)
    R->>H: handleJsonRpc(request)

    alt initialize
        H-->>C: serverInfo + capabilities
    else tools/list
        H-->>C: 9 tool definitions
    else tools/call
        H->>S: executeTool(name, args)

        alt First request (cold start)
            S->>D: fs.readFileSync
            D-->>S: Raw JSON (10.4 MB)
            S->>S: Transform + build Fuse index
        end

        alt search-medicine
            S->>S: Fuse.js fuzzy search
            S-->>H: MedicineBasic[]
        else get-pil/spc-content
            S->>A: GET /dokumenty-metadata/{code}
            A-->>S: Document metadata + ID
            S-->>H: DocumentContent (URL)
        else find-pharmacies
            S->>S: Filter pharmacy array
            S-->>H: Pharmacy[]
        else get-reimbursement
            S->>S: Map.get(sukl_code)
            S-->>H: ReimbursementInfo
        end

        H-->>C: JSON-RPC result
    end
```

---

## Komponentova architektura

```mermaid
graph LR
    subgraph "src/app/"
        Page["page.tsx<br/>(use client)"]
        Layout["layout.tsx"]
        MCPR["api/mcp/route.ts"]
        DemoR["api/demo/route.ts"]
    end

    subgraph "src/components/sections/ (12)"
        Header
        Hero
        QuickStart
        Tools
        HowItWorks
        DemoSection
        UseCases
        Stats
        Why
        FAQ
        CTA
        Footer
    end

    subgraph "src/components/demo/ (10)"
        GuidedTour["guided-tour.tsx<br/>(state machine)"]
        ChatWidget["chat-widget.tsx"]
        MessageBubble
        MedicineCard
        ExampleChips
        TourIntro
        TourStep
        TourProgress
        TourCTA
        TourValueCard
    end

    subgraph "src/components/ui/ (12)"
        ShimmerButton
        Particles
        Spotlight
        TypingAnimation
        TextGenerate
        NumberTicker
        AnimatedBeam
        BentoGrid
        CodeBlock
        Accordion
        MovingBorder
        ErrorBoundary
    end

    subgraph "src/lib/"
        Types["types.ts<br/>(7 interfaces)"]
        SUKLClient["sukl-client.ts<br/>(server-only)"]
        MCPHandler["mcp-handler.ts<br/>(9 tools)"]
        DemoHandler["demo-handler.ts"]
        Utils["utils.ts<br/>(cn helper)"]
    end

    Page --> Header
    Page --> Hero
    Page --> QuickStart
    Page --> Tools
    Page --> HowItWorks
    Page --> DemoSection
    Page --> UseCases
    Page --> Stats
    Page --> Why
    Page --> FAQ
    Page --> CTA
    Page --> Footer

    DemoSection -.->|next/dynamic| GuidedTour
    GuidedTour --> ChatWidget
    ChatWidget --> MessageBubble
    ChatWidget --> MedicineCard

    MCPR --> MCPHandler
    DemoR --> DemoHandler
    MCPHandler --> SUKLClient
    DemoHandler --> SUKLClient
    MCPHandler --> Types
    SUKLClient --> Types
```

---

## In-Memory Data Store

```mermaid
graph TB
    JSON["bundled-data.json<br/>10.4 MB"]

    subgraph "Compressed Keys"
        M["m[] — medicines (68k)"]
        A["a[] — ATC codes (6907)"]
        P["p[] — pharmacies (2662)"]
        R["r[] — reimbursements (8480)"]
    end

    subgraph "DataStore (in-memory)"
        Meds["medicines: MedicineDetail[]<br/>(68,248 items)"]
        ATC["atcCodes: Map&lt;string, ATCInfo&gt;<br/>(6,907 entries, O(1) lookup)"]
        Pharm["pharmacies: Pharmacy[]<br/>(2,662 items)"]
        Reimb["reimbursements: Map&lt;string, ReimbursementInfo&gt;<br/>(8,480 entries, O(1) lookup)"]
        FuseIdx["fuseIndex: Fuse&lt;MedicineDetail&gt;<br/>(weighted: name 0.4, substance 0.3,<br/>code 0.2, holder 0.1)"]
    end

    JSON --> M --> Meds
    JSON --> A --> ATC
    JSON --> P --> Pharm
    JSON --> R --> Reimb
    Meds --> FuseIdx
```

**Cache politika:** Data se nacitaji pri prvnim pozadavku a cachuji 1 hodinu. Na serverless (Vercel) cache zije po dobu zivotnosti instance.

---

## Demo Guided Tour — stavovy automat

```mermaid
stateDiagram-v2
    [*] --> intro: Component mount

    intro --> step_1: START_TOUR
    intro --> free: SKIP_TOUR

    step_1 --> step_2: NEXT_STEP
    step_1: Hledani leku
    step_1: query = "paralen"

    step_2 --> step_3: NEXT_STEP
    step_2: Detail leku
    step_2: uses SUKL code from step 1

    step_3 --> complete: NEXT_STEP
    step_3: ATC klasifikace
    step_3: uses ATC code from step 2

    complete --> free: START_FREE_MODE

    free --> free: user queries
    free: Volny chat rezim
    free: example chips

    note right of intro
        localStorage check:
        sukl-tour-complete
        sukl-tour-skipped
    end note
```

---

## Rate Limiting

```mermaid
graph TD
    Req[Prichozi request] --> Extract[Extrakce IP<br/>x-forwarded-for / x-real-ip]
    Extract --> Check{IP v rate map?}

    Check -->|Ne| Create[Vytvor zaznam<br/>count=1, reset=now+60s]
    Check -->|Ano| Expired{Expired?}

    Expired -->|Ano| Reset[Reset count=1<br/>novy reset timestamp]
    Expired -->|Ne| Increment[count++]

    Increment --> Limit{count > limit?}
    Limit -->|Ano| Reject[HTTP 429<br/>JSON-RPC error -32000]
    Limit -->|Ne| Allow[Zpracuj request]

    Create --> Allow
    Reset --> Allow
```

| Endpoint | Limit | Okno |
|----------|-------|------|
| `/api/mcp` | 100 req | 1 min |
| `/api/demo` | 10 req | 1 min |

> In-memory Map se resetuje pri cold startu serverless instance.

---

## Deployment

```mermaid
graph LR
    subgraph "GitHub"
        Repo["petrsovadina/SUKL-mcp"]
        Actions["GitHub Actions"]
        Cron["Cron (28. den mesice)"]
    end

    subgraph "Vercel (fra1)"
        Build["next build"]
        SSG["Static: / (landing)"]
        Serverless["Serverless: /api/*"]
    end

    subgraph "Externi"
        SUKL["opendata.sukl.cz"]
        SUKLAPI["prehledy.sukl.cz"]
    end

    Repo -->|push to main| Build
    Build --> SSG
    Build --> Serverless

    Cron --> Actions
    Actions -->|build scripts| SUKL
    Actions -->|commit data| Repo

    Serverless -.->|PIL/SPC| SUKLAPI
```

---

## Bezpecnost

- **CSP header:** `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; frame-ancestors 'none'`
- **X-Frame-Options:** DENY
- **X-Content-Type-Options:** nosniff
- **Referrer-Policy:** strict-origin-when-cross-origin
- **CORS:** Wildcard (`*`) pouze na `/api/mcp` — nezbytne pro MCP klienty
- **Rate limiting:** In-memory per IP
- **Validace vstupu:** Vse validovano pred zpracovanim (delka, typ, rozsah)
- **Error masking:** Runtime chyby vraceny jako genericka zprava, detaily pouze v logu
