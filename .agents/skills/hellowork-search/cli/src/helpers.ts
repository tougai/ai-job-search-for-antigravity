export const SEARCH_URL = "https://www.hellowork.com/fr-fr/emploi/recherche.html"
export const DETAIL_BASE_URL = "https://www.hellowork.com/fr-fr/emplois"

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

const UA = "Mozilla/5.0 (compatible; hellowork-search-cli/1.0)"

export async function htmlFetch(url: string): Promise<string> {
  const maxRetries = 4
  let delay = 500
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(url, {
      headers: {
        "User-Agent": UA,
        Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
      },
      redirect: "follow",
      signal: AbortSignal.timeout(15000),
    })
    if (response.status === 429 || response.status >= 500) {
      if (attempt === maxRetries) {
        throw new Error(`Request failed: ${response.status} ${response.statusText}`)
      }
      const jitter = Math.floor(Math.random() * 400)
      await new Promise((r) => setTimeout(r, delay + jitter))
      delay = Math.min(delay * 2, 6000)
      continue
    }
    if (response.status === 404) return ""
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`)
    }
    return response.text()
  }
  throw new Error("Request failed after max retries")
}

export interface JobCard {
  id: string
  title: string
  company: string | null
  location: string | null
  contractType: string | null
  salary: string | null
  date: string | null
  url: string
}

export interface JobDetail extends JobCard {
  description: string | null
  validThrough: string | null
  isActive: boolean
}

function numericEntity(cp: number): string {
  return cp >= 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : ""
}

export function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, dec) => numericEntity(parseInt(dec, 10)))
    .replace(/&#[xX]([0-9a-fA-F]+);/g, (_, hex) => numericEntity(parseInt(hex, 16)))
    .replace(/&nbsp;/g, " ")
}

const INVISIBLE_CHARS =
  /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F\u00AD\u061C\u180E\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFE00-\uFE0F\uFEFF\u{E0000}-\u{E007F}\u{E0100}-\u{E01EF}]/gu

export function stripInvisible<T>(value: T): T {
  if (typeof value === "string") return value.replace(INVISIBLE_CHARS, "") as T
  if (Array.isArray(value)) return value.map(stripInvisible) as T
  if (value !== null && typeof value === "object" && Object.getPrototypeOf(value) === Object.prototype) {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, stripInvisible(v)])) as T
  }
  return value
}

export function visibleHtml(html: string): string {
  return html
    .replace(/<!--[\s\S]*?(?:-->|$)/g, "")
    .replace(/<(script|style|template)\b[^>]*>[\s\S]*?(?:<\/\1\s*>|$)/gi, "")
}

export function stripTags(html: string): string {
  return visibleHtml(html).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()
}

export function clean(html: string): string {
  return decodeHtmlEntities(stripTags(html))
}

function relativeFrenchDateToIso(rel: string | null): string | null {
  if (!rel) return null
  const today = new Date()
  const lower = rel.toLowerCase()
  if (lower.includes("aujourd'hui") || lower.includes("heure") || lower.includes("minute")) {
    return today.toISOString().slice(0, 10)
  }
  if (lower.includes("hier")) {
    const d = new Date(today.getTime() - 86400000)
    return d.toISOString().slice(0, 10)
  }
  const daysMatch = lower.match(/il y a\s+(\d+)\s+jour/)
  if (daysMatch) {
    const days = parseInt(daysMatch[1], 10)
    const d = new Date(today.getTime() - days * 86400000)
    return d.toISOString().slice(0, 10)
  }
  const monthsMatch = lower.match(/il y a\s+(\d+)\s+mois/)
  if (monthsMatch) {
    const months = parseInt(monthsMatch[1], 10)
    const d = new Date(today.getTime() - months * 30 * 86400000)
    return d.toISOString().slice(0, 10)
  }
  return rel
}

export function parseJobCards(html: string): JobCard[] {
  const results: JobCard[] = []
  const chunks = html.split(/<li[^>]*data-id-storage-item-id="/i).slice(1)

  for (const chunk of chunks) {
    const idMatch = chunk.match(/^(\d+)"/)
    if (!idMatch) continue
    const id = idMatch[1]

    const titleInput = chunk.match(/<input[^>]*name="title"[^>]*value="([^"]+)"/i)
    const companyInput = chunk.match(/<input[^>]*name="company"[^>]*value="([^"]+)"/i)

    let title = titleInput ? decodeHtmlEntities(titleInput[1]).trim() : ""
    if (!title) {
      const h3Match = chunk.match(/<h3[^>]*>([\s\S]*?)<\/h3>/i)
      if (h3Match) title = clean(h3Match[1])
    }
    if (!title) continue

    const company = companyInput ? decodeHtmlEntities(companyInput[1]).trim() : null

    const locMatch = chunk.match(/data-cy="localisationCard"[^>]*>([\s\S]*?)<\/div>/i)
    const location = locMatch ? clean(locMatch[1]) || null : null

    const contractMatch = chunk.match(/data-cy="contractCard"[^>]*>([\s\S]*?)<\/div>/i)
    const contractType = contractMatch ? clean(contractMatch[1]) || null : null

    const salaryMatch = chunk.match(/data-cy="salaryCard"[^>]*>([\s\S]*?)<\/div>/i) ||
                        chunk.match(/([\d\s\u202f]+(?:-\s*[\d\s\u202f]+)?\s*€\s*\/\s*(?:an|mois|jour|heure))/i)
    const salary = salaryMatch ? clean(salaryMatch[1]) || null : null

    const relDateMatch = chunk.match(/class="[^"]*text-grey-500[^"]*"[^>]*>([\s\S]*?)<\/div>/i)
    const rawRelDate = relDateMatch ? clean(relDateMatch[1]) || null : null
    const date = relativeFrenchDateToIso(rawRelDate)

    results.push({
      id,
      title,
      company,
      location,
      contractType,
      salary,
      date,
      url: `${DETAIL_BASE_URL}/${id}.html`,
    })
  }

  return results
}

export function parseJobDetail(html: string, id: string): JobDetail {
  let title = ""
  let company: string | null = null
  let location: string | null = null
  let contractType: string | null = null
  let salary: string | null = null
  let date: string | null = null
  let validThrough: string | null = null
  let description: string | null = null

  const ldMatches = html.matchAll(/<script[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi)
  for (const m of ldMatches) {
    try {
      const parsed = JSON.parse(m[1].trim())
      if (parsed && parsed["@type"] === "JobPosting") {
        title = parsed.title ? decodeHtmlEntities(String(parsed.title)) : title
        company = parsed.hiringOrganization?.name ? decodeHtmlEntities(String(parsed.hiringOrganization.name)) : company
        const addr = parsed.jobLocation?.address
        if (addr) {
          location = [addr.addressLocality, addr.postalCode].filter(Boolean).join(" ") || location
        }
        contractType = parsed.employmentType ? String(parsed.employmentType) : contractType
        if (parsed.datePosted) {
          date = String(parsed.datePosted).slice(0, 10)
        }
        if (parsed.validThrough) {
          validThrough = String(parsed.validThrough).slice(0, 10)
        }
        if (parsed.baseSalary?.value) {
          const v = parsed.baseSalary.value
          const unit = v.unitText || ""
          if (v.minValue && v.maxValue) {
            salary = `${v.minValue} - ${v.maxValue} € ${unit}`.trim()
          } else if (v.value) {
            salary = `${v.value} € ${unit}`.trim()
          }
        }
        if (parsed.description) {
          description = decodeHtmlEntities(
            String(parsed.description)
              .replace(/<br\s*\/?>/gi, "\n")
              .replace(/<\/(?:p|h[1-6]|li|div)>/gi, "\n")
              .replace(/<li[^>]*>/gi, "- ")
              .replace(/<[^>]+>/g, " ")
              .replace(/[ \t]+/g, " ")
              .replace(/\n\s*\n+/g, "\n\n")
              .trim()
          )
        }
        break
      }
    } catch {
      // Ignore malformed JSON-LD blocks
    }
  }

  if (!title) {
    const jt = html.match(/data-cy="jobTitle"[^>]*>([\s\S]*?)<\/span>/i)
    if (jt) title = clean(jt[1])
  }
  if (!company) {
    const h1 = html.match(/<h1[^>]*id="main-content"[^>]*>([\s\S]*?)<\/h1>/i)
    if (h1) {
      const fullH1 = clean(h1[1])
      if (title && fullH1.startsWith(title)) {
        company = fullH1.slice(title.length).trim() || null
      }
    }
  }
  if (!location) {
    const mapSec = html.match(/aria-labelledby="map-section-title"[^>]*>([\s\S]*?)<\/section>/i)
    if (mapSec) {
      location = clean(mapSec[1].replace(/La carte/i, "").replace(/Localiser le poste/i, "")) || null
    }
  }
  if (!salary) {
    const salBtn = html.match(/data-cy="salary-tag-button"[^>]*>([\s\S]*?)<\/button>/i)
    if (salBtn) salary = clean(salBtn[1]) || null
  }
  if (!description) {
    const sections: string[] = []
    for (const secMatch of html.matchAll(/<section\b[^>]*>((?:(?!<\/?section\b)[\s\S])*)<\/section>/gi)) {
      const innerDecoded = decodeHtmlEntities(secMatch[1])
      if (!/Détail du poste|À noter sur ce job|Les missions|Le profil|Les avantages/i.test(innerDecoded)) continue
      const secText = decodeHtmlEntities(
        visibleHtml(innerDecoded)
          .replace(/<br\s*\/?>/gi, "\n")
          .replace(/<\/(?:p|h[1-6]|li|div)>/gi, "\n")
          .replace(/<li[^>]*>/gi, "- ")
          .replace(/<[^>]+>/g, " ")
          .replace(/[ \t]+/g, " ")
          .replace(/\n\s*\n+/g, "\n\n")
          .trim()
      )
      if (secText) sections.push(secText)
    }
    if (sections.length > 0) {
      description = sections.join("\n\n")
    }
  }
  if (!title) {
    const h1 = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i)
    title = h1 ? clean(h1[1]) : `Offre HelloWork ${id}`
  }

  return {
    id,
    title,
    company,
    location,
    contractType,
    salary,
    date,
    url: `${DETAIL_BASE_URL}/${id}.html`,
    description,
    validThrough,
    isActive: Boolean(title && description),
  }
}
