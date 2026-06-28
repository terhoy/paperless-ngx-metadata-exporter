# Paperless-ngx Metadata Exporter

En selvstendig clean-room Python/Flask-applikasjon for å søke, filtrere, vise og eksportere dokumentmetadata fra Paperless-ngx via API.

## Viktig lisens- og opprinnelsesnotat

Dette prosjektet er ment som en ny, selvstendig implementasjon basert på funksjonskrav. Ikke kopier kode, tekst, CSS, HTML eller andre filer fra ulisensierte tredjepartsrepoer inn i dette repoet.

## Funksjoner

- Kobling mot eksisterende Paperless-ngx via API-token
- Metadata-cache for korrespondenter, dokumenttyper, tagger, lagringsstier og egendefinerte felt
- Filtrering på fritekst, metadata og dato
- Dynamiske kolonner for valgte egendefinerte felt
- CSV-eksport med valgbart skilletegn
- Excel `.xlsx`-eksport
- Flerspråkstøtte via JSON-filer: norsk bokmål, engelsk, tysk og fransk
- Valgfri HTTP Basic Auth via miljøvariabler
- Docker Compose-oppsett

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

## Miljøvariabler

Se `.env.example`.

Viktigst:

```env
PAPERLESS_BASE_URL=http://din-paperless:8000
PAPERLESS_API_TOKEN=din_api_token
APP_DEFAULT_LANGUAGE=nb
APP_BASIC_AUTH_ENABLED=false
```

## CSV-skilletegn

Standard i UI er semikolon for norsk/tysk/fransk og komma for engelsk. Bruker kan overstyre ved eksport. CSV eksporteres som UTF-8 med BOM for bedre Excel-kompatibilitet.

## Egendefinerte felt

Appen forsøker å hente Paperless-ngx custom fields fra `/api/custom_fields/`. Valgte custom fields vises som dynamiske kolonner og tas med i eksport.

## GitHub-opplasting

Før du kjører `git add .`: kontroller at `.env`, API-token, `config.json`, eksportfiler og private Paperless-data ikke ligger i repoet.

```bash
git init -b main
git status
git add .
git commit -m "Initial clean-room implementation"

gh auth login
gh repo create paperless-ngx-metadata-exporter --private --source=. --remote=origin --push
```

Offentlig repo:

```bash
gh repo create paperless-ngx-metadata-exporter --public --source=. --remote=origin --push
```

Manuell remote:

```bash
git remote add origin https://github.com/<github-brukernavn>/paperless-ngx-metadata-exporter.git
git push -u origin main
```

Senere endringer:

```bash
git status
git add .
git commit -m "Beskriv endringen"
git push
```

## Sikkerhet

Se `SECURITY.md`. Ikke eksponer appen på internett uten HTTPS og autentisering/reverse proxy.
# paperless-ngx-metadata-exporter
