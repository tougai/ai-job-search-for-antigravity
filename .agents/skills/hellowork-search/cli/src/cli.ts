#!/usr/bin/env bun
import { runSearch } from "./commands/search.js"
import { runDetail } from "./commands/detail.js"
import { writeError } from "./helpers.js"

interface Flags {
  _: string[]
  [k: string]: string | boolean | string[]
}

function parseFlags(argv: string[]): Flags {
  const flags: Flags = { _: [] }
  const alias: Record<string, string> = { q: "query", l: "location", n: "limit" }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a.startsWith("--") || a.startsWith("-")) {
      const key = alias[a.replace(/^-+/, "")] ?? a.replace(/^-+/, "")
      const next = argv[i + 1]
      if (next === undefined || next.startsWith("-")) {
        flags[key] = true
      } else {
        flags[key] = next
        i++
      }
    } else {
      ;(flags._ as string[]).push(a)
    }
  }
  return flags
}

const HELP = `hellowork-cli — search jobs on HelloWork (France)

USAGE
  bun run src/cli.ts search --query "<keywords>" [--location "<city>"] [flags]
  bun run src/cli.ts detail <id|url> [--format json|plain]

SEARCH FLAGS
  --query, -q <text>      Keywords (job title, skill, or role). REQUIRED.
  --location, -l <text>   French city or region (e.g. "Paris", "Lyon"). Optional.
  --jobage <days>         Posted within N days: 1, 3, 7, 14, 30.
  --page <n>              1-indexed page. Default 1.
  --limit, -n <n>         Cap results emitted.
  --format <fmt>          json (default) | table | plain.
`

const KNOWN_FLAGS: Record<string, Set<string>> = {
  search: new Set(["query", "location", "jobage", "page", "limit", "format", "help", "h"]),
  detail: new Set(["format", "help", "h"]),
}

async function main(): Promise<number> {
  const argv = process.argv.slice(2)
  const flags = parseFlags(argv)
  const cmd = (flags._ as string[])[0]

  if (!cmd || flags.help || flags.h) {
    process.stdout.write(HELP)
    return cmd ? 0 : 1
  }

  const knownFlags = KNOWN_FLAGS[cmd]
  if (knownFlags) {
    for (const key of Object.keys(flags)) {
      if (key === "_" || knownFlags.has(key)) continue
      writeError(`unknown flag --${key} for '${cmd}'`, "UNKNOWN_FLAG")
      return 1
    }
  }

  if (cmd === "search") {
    const query = typeof flags.query === "string" ? flags.query.trim() : ""
    if (!query) {
      writeError("the --query/-q flag is required", "NO_QUERY")
      return 1
    }
    const location = typeof flags.location === "string" ? flags.location.trim() : undefined
    const page = flags.page ? parseInt(String(flags.page), 10) : 1
    if (isNaN(page) || page < 1) {
      writeError("--page must be a positive integer", "BAD_PAGE")
      return 1
    }
    const jobage = flags.jobage ? parseInt(String(flags.jobage), 10) : undefined
    const limit = flags.limit !== undefined ? parseInt(String(flags.limit), 10) : undefined
    const format = (flags.format as "json" | "table" | "plain") || "json"
    if (!["json", "table", "plain"].includes(format)) {
      writeError(`invalid --format "${format}"`, "BAD_FORMAT")
      return 1
    }
    return runSearch({ query, location, jobage, page, limit, format })
  }

  if (cmd === "detail") {
    const id = (flags._ as string[])[1]
    if (!id) {
      writeError("detail requires a job ID or URL", "NO_ID")
      return 1
    }
    const format = (flags.format as "json" | "plain") || "json"
    if (!["json", "plain"].includes(format)) {
      writeError(`invalid --format "${format}"`, "BAD_FORMAT")
      return 1
    }
    return runDetail({ id, format })
  }

  writeError(`Unknown command "${cmd}"`, "UNKNOWN_COMMAND")
  return 1
}

main().then((code) => process.exit(code))
