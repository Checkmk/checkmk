/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test, vi } from 'vitest'

import ModeHostRelationDiscoveryApp from '@/mode-host-relation-discovery/ModeHostRelationDiscoveryApp.vue'

// The client is built at import time against the real location; point it at the one msw
// listens on instead of reaching for the network.
vi.mock('cmk-ui-library/lib/rest-api-client/client', async (importOriginal) => {
  const mod = await importOriginal<Record<string, unknown>>()
  const createClientImpl = (await import('openapi-fetch')).default
  return {
    ...mod,
    default: createClientImpl({
      baseUrl: `${location.protocol}//${location.host}/api/internal`,
      credentials: 'include',
      headers: { Accept: 'application/json' },
      fetch: (...args: Parameters<typeof globalThis.fetch>) => globalThis.fetch(...args)
    })
  }
})

const ROOT = `${location.protocol}//${location.host}/api/internal`
const SUGGEST_URL = `${ROOT}/domain-types/host_relation_discovery/actions/suggest/invoke`
const SCAN_URL = `${ROOT}/domain-types/host_relation_discovery/actions/scan/invoke`
const ACCEPT_URL = `${ROOT}/domain-types/host_relation_discovery/actions/accept/invoke`
const STATUS_URL = `${ROOT}/objects/host_relation_discovery/:job_id`
const ROWS_URL = `${ROOT}/objects/host_relation_discovery/:job_id/collections/rows`

const server = setupServer()

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
})
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

const ILO = {
  word: 'ilo',
  pairs: 1,
  examples: [{ named: 'srv-01-ilo', base: 'srv-01' }],
  kind: 'management'
}

const OOB = {
  word: 'oob',
  pairs: 1,
  examples: [{ named: 'srv-02-oob', base: 'srv-02' }],
  kind: null
}

function suggesting(found: { words?: unknown[]; values?: unknown[] } = {}): void {
  server.use(
    http.post(SUGGEST_URL, () =>
      HttpResponse.json({
        hosts_scanned: 4,
        words: found.words ?? [ILO],
        values: found.values ?? [],
        label_names: ['cmdb/kind', 'cmdb/sn'],
        attribute_names: []
      })
    )
  )
}

function row(source: string, target: string, overrides: Record<string, unknown> = {}) {
  return {
    key: `${source}|management|${target}`,
    finding: 'word:ilo',
    source_host: source,
    target_host: target,
    kind: 'management',
    relation: 'management_parent',
    folders: ['', ''],
    evidence: `The name is "${target}" with "ilo" added.`,
    reason: { word: 'ilo', source: null, name: null, value: null },
    outcome: 'link',
    detail: '',
    ...overrides
  }
}

/** What a finding summary says beyond its relations, when it says nothing. */
const NOTHING_ELSE = { questions: 0, settled_groups: 0, conflicts: 0 }

interface Scanned {
  findings?: unknown[]
  relations?: unknown[]
}

/** A scan that is done at once, with a finding "ilo" of three new relations by default. */
function scanning(scanned: Scanned = {}): { sent: unknown[] } {
  const sent: unknown[] = []
  const relations = scanned.relations ?? [
    row('srv-01-ilo', 'srv-01'),
    row('srv-02-ilo', 'srv-02'),
    row('srv-03-ilo', 'srv-03')
  ]
  server.use(
    http.post(SCAN_URL, async ({ request }) => {
      sent.push(await request.json())
      return HttpResponse.json({ job_id: 'relation_scan-1' })
    }),
    http.get(STATUS_URL, ({ params }) =>
      params.job_id === 'relation_scan-1'
        ? HttpResponse.json({
            running: false,
            message: '',
            summary: '4 hosts read.',
            scan: {
              hosts_scanned: 4,
              findings: scanned.findings ?? [
                { ...NOTHING_ELSE, id: 'word:ilo', counts: { link: 3 }, samples: relations }
              ],
              conflicts: 0,
              folders: ['']
            },
            run: null
          })
        : HttpResponse.json({
            running: false,
            message: '',
            summary: 'Relation discovery finished: 2 stored, 1 could not be stored',
            scan: null,
            run: {
              findings: [
                {
                  ...NOTHING_ELSE,
                  id: 'word:ilo',
                  counts: { link: 2, not_writable: 1 },
                  samples: []
                }
              ],
              failed: 1
            }
          })
    ),
    http.get(ROWS_URL, ({ request }) => {
      const part = new URL(request.url).searchParams.get('part')
      const page = { total: 0, relations: [] as unknown[], groups: [], conflicts: [] }
      if (part === 'failed') {
        page.relations = [
          row('srv-03-ilo', 'srv-03', { outcome: 'not_writable', detail: 'No permission.' })
        ]
        page.total = 1
      } else {
        page.relations = relations
        page.total = relations.length
      }
      return HttpResponse.json(page)
    })
  )
  return { sent }
}

function accepting(): { sent: unknown[] } {
  const sent: unknown[] = []
  server.use(
    http.post(ACCEPT_URL, async ({ request }) => {
      sent.push(await request.json())
      return HttpResponse.json({ job_id: 'relation_discovery-1' })
    })
  )
  return { sent }
}

function renderApp() {
  return render(ModeHostRelationDiscoveryApp, {
    props: {
      kinds: { management: 'management_parent' },
      kind_words: { management: ['ilo', 'idrac'] },
      relation_titles: {
        management_parent: 'is management board of',
        management_child: 'is OS host of'
      },
      relation_nouns: { management_parent: 'Management board', management_child: 'OS host' },
      activate_changes_url: 'wato.py?mode=changelog'
    }
  })
}

/** Step 1 with what it starts out with. */
async function lookThroughTheHosts(): Promise<void> {
  await userEvent.click(await screen.findByRole('button', { name: 'Continue' }))
  await screen.findByRole('button', { name: 'Back' })
}

async function continueToReview(): Promise<void> {
  await lookThroughTheHosts()
  const next = await screen.findByRole('button', { name: 'Continue' })
  await waitFor(() => expect(next).not.toBeDisabled())
  await userEvent.click(next)
  await screen.findByRole('heading', { name: 'Check what will be stored' })
  await screen.findByRole('checkbox', { name: '"ilo" in the name' })
}

async function store(count: number): Promise<void> {
  await userEvent.click(
    screen.getByRole('button', { name: `Store ${count} relation${count === 1 ? '' : 's'}` })
  )
}

function suggestionsAsked(): { sent: unknown[] } {
  const sent: unknown[] = []
  server.use(
    http.post(SUGGEST_URL, async ({ request }) => {
      sent.push(await request.json())
      return HttpResponse.json({
        hosts_scanned: 4,
        words: [ILO],
        values: [],
        label_names: [],
        attribute_names: []
      })
    })
  )
  return { sent }
}

test('the hosts are read only once the user said what to look for', async () => {
  const { sent } = suggestionsAsked()

  renderApp()

  await screen.findByRole('radio', { name: 'Management board and OS host' })
  expect(screen.getByRole('radio', { name: 'Management board and OS host' })).toBeChecked()
  expect(sent).toEqual([])
})

test('the host names are what is looked in', async () => {
  const { sent } = suggestionsAsked()
  renderApp()

  await lookThroughTheHosts()

  expect(sent).toEqual([{ words: [], look_in: ['names'] }])
})

test('a step that is done says what was chosen in it', async () => {
  suggesting({ words: [ILO, OOB] })
  scanning()
  renderApp()
  await lookThroughTheHosts()

  await userEvent.click(
    screen.getByRole('checkbox', { name: '1 host is named like another host plus "oob"' })
  )
  await userEvent.click(screen.getByRole('button', { name: 'Continue' }))

  await screen.findByText('"ilo" in the name, "oob" in the name')
  screen.getByText('Management board and OS host, in the host names')
})

test('a word the relation declares starts out ticked, and says which host is which', async () => {
  suggesting()
  renderApp()

  await lookThroughTheHosts()

  expect(
    screen.getByRole('checkbox', { name: '1 host is named like another host plus "ilo"' })
  ).toBeChecked()
  screen.getByText(
    'Tick every word that marks a Management board. The host with the word in its name is the Management board, the other one its OS host.'
  )
})

test('a word no vendor uses means nothing until the user ticks it', async () => {
  suggesting({ words: [ILO, OOB] })
  renderApp()

  await lookThroughTheHosts()

  screen.getByText('Other words your host names use')
  expect(
    screen.getByRole('checkbox', { name: '1 host is named like another host plus "oob"' })
  ).not.toBeChecked()
})

test('a page with nothing found says what it looks for, and how to add it', async () => {
  suggesting({ words: [] })
  renderApp()

  await lookThroughTheHosts()

  screen.getByText(/Checkmk found no host named like another plus a word/)
  screen.getByRole('textbox', { name: 'A word in host names' })
})

test('continuing needs a ticked finding, and says so', async () => {
  suggesting({ words: [OOB] })
  renderApp()

  await lookThroughTheHosts()

  screen.getByText('To continue, tick at least one finding.')
  expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled()
})

test('every word that means a relation is a finding of its own', async () => {
  suggesting({ words: [ILO, OOB] })
  const { sent } = scanning()
  renderApp()
  await lookThroughTheHosts()

  await userEvent.click(
    screen.getByRole('checkbox', { name: '1 host is named like another host plus "oob"' })
  )
  await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
  await screen.findByRole('heading', { name: 'Check what will be stored' })

  expect(sent).toEqual([
    {
      findings: [
        { id: 'word:ilo', kind: 'management', words: ['ilo'] },
        { id: 'word:oob', kind: 'management', words: ['oob'] }
      ]
    }
  ])
})

test('a finding is stored as a whole, with a few of its relations to check it by', async () => {
  suggesting()
  scanning()
  const { sent } = accepting()
  renderApp()
  await continueToReview()

  screen.getByText('3 new')
  expect(screen.getAllByRole('checkbox', { name: /is management board of/ })).toHaveLength(3)
  await store(3)

  await waitFor(() =>
    expect(sent).toEqual([
      {
        scan_id: 'relation_scan-1',
        findings: ['word:ilo'],
        excluded: []
      }
    ])
  )
})

test('a single relation taken out of a finding is left out of the run', async () => {
  suggesting()
  scanning()
  const { sent } = accepting()
  renderApp()
  await continueToReview()

  await userEvent.click(
    screen.getByRole('checkbox', { name: 'srv-02-ilo is management board of srv-02' })
  )
  await store(2)

  await waitFor(() =>
    expect(sent).toEqual([expect.objectContaining({ excluded: ['srv-02-ilo|management|srv-02'] })])
  )
})

test('a finding taken out stores nothing', async () => {
  suggesting()
  scanning()
  renderApp()
  await continueToReview()

  await userEvent.click(screen.getByRole('checkbox', { name: '"ilo" in the name' }))

  expect(screen.getByRole('button', { name: 'Store 0 relations' })).toBeDisabled()
})

test('all relations of a finding can be looked through', async () => {
  const many = Array.from({ length: 8 }, (_unused, index) =>
    row(`srv-0${index}-ilo`, `srv-0${index}`)
  )
  suggesting()
  scanning({
    relations: many,
    findings: [{ ...NOTHING_ELSE, id: 'word:ilo', counts: { link: 8 }, samples: many.slice(0, 5) }]
  })
  renderApp()
  await continueToReview()

  await userEvent.click(screen.getByRole('button', { name: 'Show all 8 relations' }))

  await screen.findByText('srv-07-ilo')
  screen.getByRole('searchbox', { name: 'Search host names' })
})

test('the result says what came of each finding, and lists what failed', async () => {
  suggesting()
  scanning()
  accepting()
  renderApp()
  await continueToReview()

  await store(3)

  await screen.findByText('Relation discovery finished: 2 stored, 1 could not be stored')
  screen.getByText('2 stored · 1 could not be stored')
  await screen.findByText('No permission.')
  screen.getByRole('link', { name: 'Activate changes' })
})

test('a run that ends without a result says why it stored nothing', async () => {
  suggesting()
  scanning()
  accepting()
  server.use(
    http.get(STATUS_URL, ({ params }) =>
      params.job_id === 'relation_discovery-1'
        ? HttpResponse.json({
            running: false,
            message: '',
            summary: 'The scan is gone. Scan again.',
            scan: null,
            run: null
          })
        : undefined
    )
  )
  renderApp()
  await continueToReview()

  await store(3)

  await screen.findByText('The relations could not be stored. The scan is gone. Scan again.')
})

test('going back to the findings keeps the scan while nothing was changed', async () => {
  suggesting()
  const { sent } = scanning()
  renderApp()
  await continueToReview()

  await userEvent.click(screen.getByRole('button', { name: 'Back to the findings' }))
  await userEvent.click(await screen.findByRole('button', { name: 'Back to what was found' }))

  await screen.findByRole('heading', { name: 'Check what will be stored' })
  expect(sent).toHaveLength(1)
})

test('a word the user adds is looked up and can be removed again', async () => {
  const asked: unknown[] = []
  server.use(
    http.post(SUGGEST_URL, async ({ request }) => {
      const body = (await request.json()) as { words: string[] }
      asked.push(body)
      return HttpResponse.json({
        hosts_scanned: 4,
        words: body.words.includes('oob') ? [ILO, OOB] : [ILO],
        values: [],
        label_names: [],
        attribute_names: []
      })
    })
  )
  renderApp()
  await lookThroughTheHosts()

  await userEvent.click(await screen.findByRole('button', { name: 'Something missing?' }))
  await userEvent.type(screen.getByRole('textbox', { name: 'A word in host names' }), 'oob')
  await userEvent.click(screen.getByRole('button', { name: 'Add word' }))

  const added = await screen.findByRole('checkbox', {
    name: '1 host is named like another host plus "oob"'
  })
  expect(added).toBeChecked()
  await userEvent.click(screen.getByTitle('Remove the word "oob"'))

  await waitFor(() => expect(screen.queryByText(/plus "oob"/)).toBeNull())
  expect(asked.at(-1)).toEqual({ words: [], look_in: ['names'] })
})

test('every relation a search matches can be taken out at once', async () => {
  const many = Array.from({ length: 8 }, (_unused, index) =>
    row(`srv-0${index}-ilo`, `srv-0${index}`)
  )
  suggesting()
  scanning({
    relations: many,
    findings: [{ ...NOTHING_ELSE, id: 'word:ilo', counts: { link: 8 }, samples: many.slice(0, 5) }]
  })
  server.use(
    http.get(ROWS_URL, ({ request }) => {
      const query = new URL(request.url).searchParams
      const matching = many.filter((one) => one.source_host.includes(query.get('search') ?? ''))
      return HttpResponse.json({
        total: matching.length,
        relations: matching,
        groups: [],
        conflicts: [],
        keys: query.get('all_keys') === 'true' ? matching.map((one) => one.key) : []
      })
    })
  )
  const { sent } = accepting()
  renderApp()
  await continueToReview()

  await userEvent.click(screen.getByRole('button', { name: 'Show all 8 relations' }))
  await userEvent.type(await screen.findByRole('searchbox', { name: 'Search host names' }), 'srv-0')
  await userEvent.keyboard('{Enter}')
  await screen.findByText('8 relations match')
  await userEvent.click(screen.getByRole('button', { name: 'Untick all of them' }))

  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Store 0 relations' })).toBeDisabled()
  )
  expect(sent).toEqual([])
})
