"""
OPRAVA PRO: PDF parsing - CSV filename lookup a text extraction

Tento soubor obsahuje opravu funkcí get_pil_content a get_spc_content:
- Používá CSV tabulku dlp_nazvydokumentu pro získání správných názvů souborů
- Stahuje a parsuje PDF pomocí pypdf knihovny
- Vrací plný text, ne jen URL

NÁVOD NA APLIKACI:
1. Přidat importy na začátek server.py:
   from pypdf import PdfReader
   import io

2. V server.py přidat konstantu BASE_URL (pokud neexistuje):
   BASE_URL = "https://prehledy.sukl.cz"

3. Nahradit get_document_text v document_parser.py touto verzí

4. Aktualizovat @mcp.tool() funkce get_pil_content a get_spc_content v server.py
   aby volaly parser.get_document_text() s parametry sukl_code a doc_type
"""

from pypdf import PdfReader
import io


async def get_document_text(
    sukl_code: str,
    doc_type: str,  # 'pil' nebo 'spc'
    loader,
) -> str | None:
    """
    Stáhne a extrahuje text z PDF dokumentu.

    OPRAVA v4.0: Načte filename z CSV (dlp_nazvydokumentu.csv)
    - Před: Hardcoded URL pattern {kod}.pdf
    - Po: Lookup v CSV pro správný filename

    Proces:
    1. Načíst filename z CSV (dlp_nazvydokumentu.csv)
    2. Stáhnout PDF z https://prehledy.sukl.cz/{pil|spc}/{filename}
    3. Extrahovat text pomocí pypdf knihovny
    4. Vrátit plný text obsah

    Args:
        sukl_code: SÚKL kód (7 číslic)
        doc_type: 'pil' (příbalový leták) nebo 'spc' (souhrn údajů)
        loader: SUKLDataLoader instance pro přístup k CSV

    Returns:
        Plný text dokumentu nebo None
    """
    # KROK 1: Načíst filename z CSV
    try:
        df_docs = loader.get_table("dlp_nazvydokumentu")

        if df_docs is None or df_docs.empty:
            print(f"   ⚠️  dlp_nazvydokumentu.csv not available")
            return None

        # Najít záznam v CSV
        sukl_int = int(sukl_code)
        row = df_docs[df_docs["KOD_SUKL"] == sukl_int]

        if row.empty:
            print(f"   ℹ️  No document record for {sukl_code}")
            return None

        column_name = doc_type.upper()  # 'PIL' nebo 'SPC'
        filename = row.iloc[0][column_name]

        if pd.isna(filename) or not filename:
            print(f"   ℹ️  No {doc_type} file for {sukl_code}")
            return None

    except Exception as e:
        print(f"❌ Error looking up document: {e}")
        return None

    # KROK 2: Sestavit URL
    base_url = "https://prehledy.sukl.cz"
    url = f"{base_url}/{doc_type.lower()}/{filename}"
    print(f"📥 Downloading: {url}")

    # KROK 3: Stáhnout PDF
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            # KROK 4: Parsovat PDF pomocí pypdf
            pdf_file = io.BytesIO(response.content)
            reader = PdfReader(pdf_file)

            text_parts = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_parts.append(text.strip())

            full_text = "\n\n".join(text_parts)

            if not full_text:
                print(f"⚠️  Empty text extracted from {filename}")
                return None

            print(f"   ✅ Extracted {len(full_text):,} chars from {len(reader.pages)} pages")
            return full_text

    except httpx.HTTPError as e:
        print(f"❌ HTTP error downloading {url}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error fetching/parsing PDF: {e}")
        return None
