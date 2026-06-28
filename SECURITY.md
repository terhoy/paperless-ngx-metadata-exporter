# Sikkerhet

- Ikke commit `.env`, `config.json`, API-token, passord eller eksporterte dokumentdata.
- Bruk miljøvariabler i Docker når mulig.
- Hvis appen eksponeres utenfor LAN, bruk HTTPS og autentisering.
- Basic Auth kan aktiveres med `APP_BASIC_AUTH_ENABLED=true`.
- API-token logges ikke av applikasjonen med vilje. Unngå debug-logging i produksjon.
- Bruk helst reverse proxy med TLS og eventuell SSO/IP-filter hvis appen eksponeres bredere.
