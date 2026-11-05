# HelloWork URL & Parsing Reference

## Endpoints

- **Search (GET)**: `https://www.hellowork.com/fr-fr/emploi/recherche.html?k=<query>&l=<location>&p=<page>&d=<date_code>`
  - `k`: keywords
  - `l`: location string (e.g. `Paris`, `Lyon`)
  - `p`: 1-indexed page number
  - `d`: recency filter (`1` = today/1 day, `3` = 3 days, `7` = 7 days, `14` = 14 days, `30` = 30 days, `all` = default)
- **Detail (GET)**: `https://www.hellowork.com/fr-fr/emplois/<id>.html`

## Search HTML Anchors

Each job listing card is an `<li data-id-storage-item-id="<id>">` containing:
- `<input name="offerId" type="hidden" value="<id>"/>`
- `<input name="title" type="hidden" value="<title>"/>`
- `<input name="company" type="hidden" value="<company>"/>`
- `data-cy="localisationCard"` for location
- `data-cy="contractCard"` for contract type (CDI, CDD, etc.)
- Relative age inside `<div class="typo-s text-grey-500...">il y a X jours</div>`

## Detail Page Anchors

Each detail page embeds a `<script type="application/ld+json">` with `"@type": "JobPosting"`, providing:
- `title`
- `description` (HTML)
- `datePosted` (ISO date)
- `validThrough`
- `employmentType`
- `hiringOrganization.name`
- `jobLocation.address.addressLocality` / `postalCode`
- `baseSalary` (when disclosed)
