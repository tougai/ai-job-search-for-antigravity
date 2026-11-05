import { describe, expect, test } from "bun:test"
import { parseJobCards, parseJobDetail } from "../src/helpers.js"
import { normalizeId } from "../src/commands/detail.js"

describe("hellowork-search parsing", () => {
  test("parses job card HTML", () => {
    const html = `
      <ul>
        <li data-id-storage-item-id="71820699">
          <input name="offerId" type="hidden" value="71820699"/>
          <input name="title" type="hidden" value="Data Engineer H/F"/>
          <input name="company" type="hidden" value="Groupe Karavel"/>
          <div data-cy="localisationCard">Paris 10e - 75</div>
          <div data-cy="contractCard">CDI</div>
          <div class="typo-s text-grey-500">il y a 2 jours</div>
        </li>
      </ul>
    `
    const cards = parseJobCards(html)
    expect(cards.length).toBe(1)
    expect(cards[0].id).toBe("71820699")
    expect(cards[0].title).toBe("Data Engineer H/F")
    expect(cards[0].company).toBe("Groupe Karavel")
    expect(cards[0].location).toBe("Paris 10e - 75")
    expect(cards[0].contractType).toBe("CDI")
    expect(cards[0].url).toBe("https://www.hellowork.com/fr-fr/emplois/71820699.html")
  })

  test("normalizes HelloWork IDs and URLs", () => {
    expect(normalizeId("71820699")).toBe("71820699")
    expect(normalizeId("https://www.hellowork.com/fr-fr/emplois/71820699.html")).toBe("71820699")
    expect(normalizeId("https://evil.com/fr-fr/emplois/71820699.html")).toBeNull()
  })

  test("parses job detail sections", () => {
    const html = `
      <h1 id="main-content"><span data-cy="jobTitle">Data Engineer H/F</span> Groupe Karavel</h1>
      <button data-cy="salary-tag-button">50 000 - 60 000 € / an</button>
      <section class="peer flex flex-col">
        <h2><span>D&#xE9;tail du poste</span></h2>
        <div>Missions principales : Développer les pipelines Python et Snowflake.</div>
      </section>
    `
    const detail = parseJobDetail(html, "71820699")
    expect(detail.title).toBe("Data Engineer H/F")
    expect(detail.company).toBe("Groupe Karavel")
    expect(detail.salary).toBe("50 000 - 60 000 € / an")
    expect(detail.description).toContain("Missions principales")
    expect(detail.isActive).toBe(true)
  })
})
