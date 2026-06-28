# Paperless-ngx Metadata Exporter

Clean-room Python/Flask-applikasjon for å søke, filtrere, vise og eksportere dokumentmetadata fra Paperless-ngx via API.

## Nytt i v0.2

- PDF-eksport for A4 innholdsark / arkivindeks.
- PDF-eksport for etikettark.
- PDF-eksport for kombinert innholdsark + etiketter.
- Demo-modus for testing uten Paperless-ngx.
- Datofelt i UI vises nå som lesbare navn, ikke `created`/`added`.
- `reportlab` lagt til for PDF-generering.

## Rask start

```bash
cp .env.example .env
# Rediger .env med PAPERLESS_BASE_URL og PAPERLESS_API_TOKEN
docker compose up -d --build
```

Åpne:

```text
http://localhost:5001
```

## Test uten Paperless

Sett dette i `.env`:

```env
APP_DEMO_MODE=true
```

Da kan du teste tabell, CSV, Excel, A4 innholdsark og etiketter med eksempeldata.

## PDF-funksjoner

Eksportseksjonen støtter:

- CSV
- Excel `.xlsx`
- A4 innholdsark PDF
- Etikettark PDF
- Kombinert PDF

Standard etikettmal er nå **Avery L4745REV-25 / L4745**:

- A4-ark
- 8 etiketter per ark
- 2 kolonner x 4 rader
- 96 x 63,5 mm per etikett
- avtagbart lim

Det finnes også en eldre/generisk testmal:

- store etiketter ca. 99 x 68 mm
- rygg-/sideetiketter ca. 38 x 192 mm

I UI kan du justere X-/Y-forskyvning i millimeter dersom skriveren ikke treffer helt på etikettarket.

Ved utskrift av etiketter:

```text
Skalering: 100 %
Ikke bruk: Tilpass til side
Papir: A4
```

## Viktig sikkerhet

Ikke commit:

- `.env`
- API-token
- `config.json`
- eksporterte dokumentdata
- private PDF-/CSV-/Excel-filer


## Penere feilmeldinger i UI

Fra v0.4 vises tilkoblingsfeil mot Paperless-ngx som en tydelig statusboks i UI i stedet for rå JSON. Hvis Paperless ikke er tilgjengelig, kan du teste layout og PDF-funksjoner med:

```env
APP_DEMO_MODE=true
```

## Synlig valgt etikettmal

Knappen for etikett-PDF viser nå valgt etikettmal, for eksempel `Avery L4745REV-25 / L4745`, slik at det er tydelig hvilken mal PDF-en genereres for.


## v0.5 - forbedret eksport og etikett-UI

- Alle eksportknapper bruker nå `fetch()` og blob-nedlasting i stedet for direkte navigering til API-endepunkt.
- Dermed vises ikke rå JSON-feil i nettleseren dersom Paperless-ngx ikke er tilgjengelig.
- Feil vises som lesbar statusboks i appen.
- Valgt etikettmal vises under nedtrekksfeltet for etikettmal, ikke inne i PDF-knappen.
- `Etikett PDF`-knappen er igjen kort og ryddig.
- X-/Y-justering er flyttet til "Avanserte etikettinnstillinger".


## v0.6 prototype - strammere UI

Dette er en UI-prototype med mindre støy i hovedbildet:

- Søk og de vanligste filtrene ligger øverst.
- Sjeldnere filtre er flyttet til "Flere filtre".
- Eksport er redusert til CSV, Excel og Arkivutskrift.
- Saksfelter, etikettmal og PDF-valg er flyttet inn i eget Arkivutskrift-panel.
- X-/Y-justering ligger under avanserte etikettinnstillinger.
- Kombinert arkiv-PDF forsøker nå å slå sammen innholdsark og etikettark med `pypdf`.
