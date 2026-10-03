---
name: get-started
description: Použij při požadavku na vyhledání českého léčivého přípravku, katalogový detail, klasifikaci ATC nebo odkaz na oficiální PIL/SPC.
---

Pracuj pouze s názvem přípravku, látkou, veřejným kódem SÚKL nebo ATC. Do nástrojů nepředávej jména lidí, diagnózy, rodná čísla ani text celé konverzace.

Pro hledání použij `search_medicines`; pro známý kód `get_medicine`. Více nalezených balení rozliš podle síly, formy a balení. Nevymýšlej kódy ani nevybírej léčbu pro konkrétního člověka. Pokud uživatel chce přehledné zobrazení, použij `display_medicines` s nejvýše deseti relevantními kódy. Karty jsou doplňkem k textové odpovědi.

Pro ATC použij `get_atc_group`. Příslušnost ke stejné skupině nepotvrzuje zaměnitelnost. Pro PIL/SPC použij `get_medicine_document`; vrací odkaz, nikoli přečtený obsah PDF. Odpověď proto neoznačuj za výklad dokumentu bez jeho skutečného načtení.

Uveď platnost katalogu z `provenance.source_as_of` a `source_valid_until`. Pokud chybí, uveď, že platnost není ověřena. Nezaměňuj `bundle_created_at` za platnost dat. Neprezentuj registraci jako skladovou dostupnost. Uvedené látky ověř v oficiálním dokumentu, zejména u kombinovaných přípravků.

Při `not_found`, `document_not_found` nebo `isError` sděl odpovídající stav. Plugin nezjišťuje aktuální zásoby, ceny, úhrady nebo lékové interakce, neobjednává léky a neposkytuje osobní doporučení dávkování. Nevkládej citlivé osobní údaje do vyhledávacího dotazu. Zdůrazni nezávislost projektu na SÚKL, pokud se uživatel ptá na jeho provozovatele.
