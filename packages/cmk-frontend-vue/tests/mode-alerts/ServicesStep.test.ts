/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import {
  type WizardContext,
  wizardContextProvider
} from 'cmk-ui-library/components/CmkWizard/utils.ts'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { afterEach, expect, test, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import type { FoundService, ServiceSearchResult, UnitSummary } from '@/mode-alerts/service-client'
import ServicesStep from '@/mode-alerts/steps/ServicesStep.vue'
import { type AlertModel, emptyAlert } from '@/mode-alerts/types'

import { CONDITIONS_SPEC, FOLDER_PATHS, MAIN_FOLDER } from './conditions-spec'

const SEARCH = '/domain-types/telemetry_alert/actions/search_services/invoke'

type SearchBody = {
  service_match: { mode: string; pattern: string }
  conditions?: { folder: string }
}

function service(host: string, name: string, extra: Partial<FoundService> = {}): FoundService {
  return {
    host_name: host,
    service_name: name,
    discovered: true,
    unit: '',
    ...extra
  }
}

// What the server answers for the services it found, summarised like the server does.
function searchResult(
  found: FoundService[],
  extra: Partial<ServiceSearchResult> = {}
): ServiceSearchResult {
  const units: UnitSummary[] = []
  for (const entry of found) {
    const known = units.find((unit) => unit.unit === entry.unit)
    if (known === undefined) {
      units.push({ unit: entry.unit ?? null, count: 1 })
    } else {
      known.count += 1
    }
  }
  const undiscovered = found.filter((entry) => !entry.discovered)
  return {
    services: found,
    total: found.length,
    hidden: 0,
    units,
    undiscovered: undiscovered.length,
    undiscovered_hosts: [...new Set(undiscovered.map((entry) => entry.host_name))],
    incomplete_configurations: [],
    unreachable_sites: [],
    service_names: [...new Set(found.map((entry) => entry.service_name))].sort(),
    service_names_truncated: false,
    ...extra
  }
}

// The answer to any search, so a test only has to say what was found.
let answer: ServiceSearchResult = searchResult([])
// The body of the step's latest own search, not the dropdown's.
let lastSearch: SearchBody | null = null

// The dropdown searches for names containing what was typed, the step for the pattern itself.
function isSuggestion(body: SearchBody): boolean {
  return body.service_match.pattern.startsWith('.*')
}

const server = useMswServer(
  restApiHttp.post(SEARCH, async ({ request, response }) => {
    const body = (await request.json()) as SearchBody
    if (!isSuggestion(body)) {
      lastSearch = body
    }
    return response(200).json(answer)
  })
)

afterEach(() => {
  cleanup()
  answer = searchResult([])
  lastSearch = null
})

function renderStep(alert: Partial<AlertModel> = {}) {
  const model = ref<AlertModel>({ ...emptyAlert({ folder_path: MAIN_FOLDER }), ...alert })
  const navigation = {
    next: vi.fn<() => void>(),
    prev: vi.fn<() => void>(),
    goto: vi.fn<(index: number) => void>()
  }
  const context: WizardContext = {
    mode: () => 'guided',
    isSelected: () => true,
    navigation
  }
  const wrapper = defineComponent({
    components: { ServicesStep },
    setup() {
      return { model, spec: CONDITIONS_SPEC, folderPaths: FOLDER_PATHS }
    },
    template: `<ServicesStep v-model="model" :conditions-spec="spec" :folder-paths="folderPaths" :index="1" :is-completed="() => false" />`
  })
  render(wrapper, {
    global: { provide: { [wizardContextProvider as symbol]: context } }
  })
  return { model, navigation }
}

// Both fields are CmkDropdowns, whose accessible name is their `label`; the popover
// carries a filter input labelled "filter" and one option per suggestion.
function combobox(name: string): HTMLElement {
  return screen.getByRole('combobox', { name })
}

async function open(name: string): Promise<void> {
  const trigger = combobox(name)
  await waitFor(() => expect(trigger).toBeEnabled())
  void userEvent.click(trigger)
}

async function pickServiceName(name: string): Promise<void> {
  await open('Service name')
  await userEvent.click(await screen.findByRole('option', { name }))
}

// A name the site does not offer is reachable through the typed-name suggestion.
async function typeServiceName(name: string): Promise<void> {
  await open('Service name')
  await userEvent.type(await screen.findByRole('textbox', { name: 'filter' }), name)
  await userEvent.click(await screen.findByRole('option', { name }))
}

async function pickMatchType(title: string): Promise<void> {
  await open('Match service name by')
  await userEvent.click(await screen.findByRole('option', { name: title }))
}

async function settle(): Promise<void> {
  for (let tick = 0; tick < 5; tick++) {
    await new Promise((resolve) => setTimeout(resolve, 0))
  }
}

// Holds the step's own exact searches until released.
function heldExactSearch(): { release: () => void; started: () => boolean } {
  const pending: Array<() => void> = []
  server.use(
    restApiHttp.post(SEARCH, async ({ request, response }) => {
      const body = (await request.json()) as SearchBody
      if (body.service_match.mode === 'exact') {
        await new Promise<void>((resolve) => pending.push(resolve))
      }
      return response(200).json(answer)
    })
  )
  return {
    release: () => pending.splice(0).forEach((resolve) => resolve()),
    started: () => pending.length > 0
  }
}

async function next(): Promise<void> {
  await userEvent.click(screen.getByRole('button', { name: /next step/i }))
}

test('choosing a service name lists the custom services it matches', async () => {
  answer = searchResult([
    service('web01', 'HTTP request duration'),
    service('web02', 'HTTP request duration')
  ])
  renderStep()

  await pickServiceName('HTTP request duration')

  await waitFor(() => {
    expect(screen.getByText('web01')).toBeInTheDocument()
  })
  expect(screen.getByText('web02')).toBeInTheDocument()
})

test('the names of the services found are offered as choices', async () => {
  answer = searchResult([
    service('web01', 'HTTP request duration'),
    service('db01', 'Query duration', { discovered: false })
  ])
  renderStep()

  await open('Service name')

  expect(await screen.findByRole('option', { name: 'HTTP request duration' })).toBeInTheDocument()
  expect(screen.getByRole('option', { name: 'Query duration' })).toBeInTheDocument()
})

test('the choices are searched on the hosts the conditions select', async () => {
  const sent: SearchBody[] = []
  server.use(
    restApiHttp.post(SEARCH, async ({ request, response }) => {
      sent.push((await request.json()) as SearchBody)
      return response(200).json(answer)
    })
  )
  renderStep()

  await open('Service name')

  await waitFor(() => expect(sent.some(isSuggestion)).toBe(true))
  expect(sent.find(isSuggestion)?.conditions?.folder).toBe('/')
})

test('the number of all matching services is reported', async () => {
  answer = searchResult([service('web01', 'HTTP request duration')], { total: 3, hidden: 2 })
  renderStep()

  await pickServiceName('HTTP request duration')

  await waitFor(() => {
    expect(screen.getByText(/Matching services/)).toHaveTextContent('(3)')
  })
})

test('no results are shown before a search has run', () => {
  renderStep({ servicePattern: 'HTTP request duration' })

  expect(screen.queryByText(/Matching services/)).not.toBeInTheDocument()
})

test('a service name matching nothing says so without waiting for the next step', async () => {
  renderStep()

  await typeServiceName('nonexistent')

  await waitFor(() => {
    expect(screen.getByText(/No matching services/)).toBeInTheDocument()
  })
  expect(screen.queryByText(/Matching services/)).not.toBeInTheDocument()
})

test('a missing service name blocks navigation with a required error', async () => {
  const { navigation } = renderStep()

  await next()

  await waitFor(() => {
    expect(screen.getByText('A service name is required')).toBeInTheDocument()
  })
  expect(navigation.next).not.toHaveBeenCalled()
})

test('a service name matching nothing blocks navigation', async () => {
  const { navigation } = renderStep({ servicePattern: 'nonexistent' })

  await next()

  await waitFor(() => {
    expect(screen.getByText(/No matching services/)).toBeInTheDocument()
  })
  expect(navigation.next).not.toHaveBeenCalled()
})

test('a regular expression the server refuses blocks navigation and says why', async () => {
  server.use(
    restApiHttp.post(SEARCH, async ({ request, response }) => {
      if (isSuggestion((await request.json()) as SearchBody)) {
        return response(200).json(answer)
      }
      return response.untyped(
        Response.json(
          {
            title: 'Bad Request',
            status: 400,
            detail: 'These fields have problems: body.service_match.regex.pattern',
            fields: {
              'body.service_match.regex.pattern': {
                loc: ['body', 'service_match', 'regex', 'pattern'],
                msg: 'Value error, Not a valid regular expression: unterminated character set',
                type: 'value_error'
              }
            }
          },
          { status: 400 }
        )
      )
    })
  )
  const { navigation } = renderStep({ matchType: 'regex', servicePattern: '[' })

  await next()

  expect(
    await screen.findByText('Not a valid regular expression: unterminated character set')
  ).toBeInTheDocument()
  expect(screen.getByRole('textbox', { name: /Service name/ })).toHaveAttribute(
    'aria-invalid',
    'true'
  )
  expect(navigation.next).not.toHaveBeenCalled()
})

test('a search the server cannot answer shows its reason and blocks navigation', async () => {
  server.use(
    restApiHttp.post(SEARCH, async ({ request, response }) => {
      if (isSuggestion((await request.json()) as SearchBody)) {
        return response(200).json(answer)
      }
      return response.untyped(
        Response.json(
          {
            title: 'The service search failed',
            detail: 'This site has no metric backend to find the custom services in.',
            status: 503
          },
          { status: 503 }
        )
      )
    })
  )
  const { navigation } = renderStep({ servicePattern: 'HTTP request duration' })

  await next()

  expect(
    await screen.findByText(
      'The service search failed: This site has no metric backend to find the custom services in.'
    )
  ).toBeInTheDocument()
  expect(navigation.next).not.toHaveBeenCalled()
})

test('a failing search blocks navigation and says so', async () => {
  server.use(
    restApiHttp.post(SEARCH, ({ response }) =>
      response.untyped(Response.json({ title: 'Internal error', status: 500 }, { status: 500 }))
    )
  )
  const { navigation } = renderStep({ servicePattern: 'HTTP request duration' })

  await next()

  expect(await screen.findByText('Failed to search for custom services.')).toBeInTheDocument()
  expect(navigation.next).not.toHaveBeenCalled()
})

test('the service name help explains both match types', async () => {
  renderStep()

  await userEvent.click(screen.getByRole('button', { name: 'How are service names matched?' }))

  const help = await screen.findByRole('tooltip')
  expect(help).toHaveTextContent(/Exact matching needs the complete service name/)
  expect(help).toHaveTextContent(/matches from the start of the service name/)
})

test('at least one matching service continues to the next step', async () => {
  answer = searchResult([service('web01', 'HTTP request duration')])
  const { navigation } = renderStep({ servicePattern: 'HTTP request duration' })

  await next()

  await waitFor(() => {
    expect(navigation.next).toHaveBeenCalled()
  })
})

test('services only on hosts the user cannot see still continue to the next step', async () => {
  answer = searchResult([], {
    total: 1,
    hidden: 1,
    units: [{ unit: 'ms', count: 1 }]
  })
  const { navigation } = renderStep({ servicePattern: 'HTTP request duration' })

  await next()

  await waitFor(() => {
    expect(navigation.next).toHaveBeenCalled()
  })
})

test('services in different units block navigation and name the units', async () => {
  answer = searchResult([
    service('web01', 'HTTP request duration', { unit: 'ms' }),
    service('web01', 'HTTP queue length', { unit: '' })
  ])
  const { navigation } = renderStep({ matchType: 'regex', servicePattern: 'HTTP' })

  await next()

  expect(await screen.findByText(/different units: ms, no unit\./)).toBeInTheDocument()
  expect(navigation.next).not.toHaveBeenCalled()
})

test('services in different units say so without waiting for the next step', async () => {
  answer = searchResult([
    service('web01', 'HTTP request duration', { unit: 'ms' }),
    service('web01', 'HTTP queue length', { unit: '' })
  ])
  const { navigation } = renderStep()

  await typeServiceName('HTTP')

  expect(await screen.findByText(/different units/)).toBeInTheDocument()
  expect(navigation.next).not.toHaveBeenCalled()
})

test('narrowing the service name to one unit clears the unit warning', async () => {
  answer = searchResult([
    service('web01', 'HTTP request duration', { unit: 'ms' }),
    service('web01', 'HTTP queue length', { unit: '' })
  ])
  renderStep()
  await typeServiceName('HTTP')
  await screen.findByText(/different units/)

  answer = searchResult([service('web01', 'HTTP request duration', { unit: 'ms' })])
  await pickServiceName('HTTP request duration')

  await waitFor(() => {
    expect(screen.getByText('ms')).toBeInTheDocument()
    expect(screen.queryByText('no unit')).not.toBeInTheDocument()
  })
  expect(screen.queryByText(/different units/)).not.toBeInTheDocument()
})

test('an unknown unit counts as a unit of its own', async () => {
  answer = searchResult([
    service('web01', 'HTTP request duration', { unit: 'ms' }),
    service('app03', 'HTTP request duration', { unit: null })
  ])
  const { navigation } = renderStep({ servicePattern: 'HTTP request duration' })

  await next()

  expect(await screen.findByText(/different units: ms, unit unknown\./)).toBeInTheDocument()
  expect(navigation.next).not.toHaveBeenCalled()
})

test('a unit only on hosts the user cannot see is named too', async () => {
  answer = searchResult([service('web01', 'HTTP request duration', { unit: 'ms' })], {
    total: 2,
    hidden: 1,
    units: [
      { unit: 'ms', count: 1 },
      { unit: 'B/s', count: 1 }
    ]
  })
  renderStep({ servicePattern: 'HTTP request duration' })

  await next()

  expect(await screen.findByText(/different units: ms, B\/s\./)).toBeInTheDocument()
})

test('each listed service shows its unit, so the user can tell the services apart', async () => {
  answer = searchResult([
    service('web01', 'HTTP request duration', { unit: 'ms' }),
    service('web01', 'HTTP queue length', { unit: '' }),
    service('web02', 'HTTP queue length', { unit: null })
  ])
  renderStep()

  await typeServiceName('HTTP')

  expect(await screen.findByText('ms')).toBeInTheDocument()
  expect(screen.getByText('no unit')).toBeInTheDocument()
  expect(screen.getByText('unit unknown (no recent data)')).toBeInTheDocument()
})

test('a service not discovered yet is marked and the hosts needing discovery are named', async () => {
  answer = searchResult([
    service('web01', 'cart requests'),
    service('app01', 'cart requests', { discovered: false }),
    service('app02', 'cart requests', { discovered: false })
  ])
  renderStep()

  await pickServiceName('cart requests')

  expect(await screen.findAllByText('not yet discovered')).toHaveLength(2)
  expect(
    screen.getByText(
      '2 of these services are not discovered yet. The alert applies to them only after a service discovery on app01, app02.'
    )
  ).toBeInTheDocument()
})

test('services on hosts the user cannot see are counted', async () => {
  answer = searchResult([service('web01', 'cart requests')], { total: 4, hidden: 3 })
  renderStep()

  await pickServiceName('cart requests')

  expect(
    await screen.findByText('3 more services are on hosts you cannot see.')
  ).toBeInTheDocument()
})

test('services beyond the listed ones are counted', async () => {
  answer = searchResult([service('web01', 'cart requests')], { total: 250 })
  renderStep()

  await pickServiceName('cart requests')

  expect(
    await screen.findByText(
      '249 more services are not listed. Refine the service name to see them.'
    )
  ).toBeInTheDocument()
})

test('a single service on a host the user cannot see is counted in the singular', async () => {
  answer = searchResult([service('web01', 'cart requests')], { total: 2, hidden: 1 })
  renderStep()

  await pickServiceName('cart requests')

  expect(await screen.findByText('1 more service is on a host you cannot see.')).toBeInTheDocument()
})

test('a single service beyond the listed ones is counted in the singular', async () => {
  answer = searchResult([service('web01', 'cart requests')], { total: 2 })
  renderStep()

  await pickServiceName('cart requests')

  expect(
    await screen.findByText('1 more service is not listed. Refine the service name to see it.')
  ).toBeInTheDocument()
})

test('a single service not discovered yet is told in the singular', async () => {
  answer = searchResult([
    service('web01', 'cart requests'),
    service('app01', 'cart requests', { discovered: false })
  ])
  renderStep()

  await pickServiceName('cart requests')

  expect(
    await screen.findByText(
      '1 of these services is not discovered yet. The alert applies to it only after a service discovery on app01.'
    )
  ).toBeInTheDocument()
})

test('a custom service with more series than can be checked is named', async () => {
  answer = searchResult([service('web01', 'cart requests')], {
    incomplete_configurations: ['by_pod']
  })
  renderStep()

  await pickServiceName('cart requests')

  expect(await screen.findByText(/^The custom service by_pod has more series/)).toBeInTheDocument()
})

test('several custom services with more series than can be checked are named', async () => {
  answer = searchResult([service('web01', 'cart requests')], {
    incomplete_configurations: ['by_pod', 'by_route']
  })
  renderStep()

  await pickServiceName('cart requests')

  expect(
    await screen.findByText(/^The custom services by_pod, by_route have more series/)
  ).toBeInTheDocument()
})

test('a site that did not answer is named', async () => {
  answer = searchResult([service('web01', 'cart requests')], { unreachable_sites: ['remote'] })
  renderStep()

  await pickServiceName('cart requests')

  expect(
    await screen.findByText('The site remote did not answer, so its services are missing.')
  ).toBeInTheDocument()
})

test('several sites that did not answer are named', async () => {
  answer = searchResult([service('web01', 'cart requests')], {
    unreachable_sites: ['remote', 'branch']
  })
  renderStep()

  await pickServiceName('cart requests')

  expect(
    await screen.findByText(
      'The sites remote, branch did not answer, so their services are missing.'
    )
  ).toBeInTheDocument()
})

test('a regular expression is typed freely instead of picked from suggestions', async () => {
  const { model } = renderStep()

  await pickMatchType('Regular expression')
  await userEvent.type(screen.getByRole('textbox', { name: /^Service name/ }), 'HTTP.*')

  expect(model.value.servicePattern).toBe('HTTP.*')
  expect(screen.queryByRole('combobox', { name: 'Service name' })).not.toBeInTheDocument()
})

test('changing the match type discards the results of the previous search', async () => {
  answer = searchResult([service('web01', 'HTTP request duration')])
  renderStep()

  await pickServiceName('HTTP request duration')
  await waitFor(() => {
    expect(screen.getByText('web01')).toBeInTheDocument()
  })

  await pickMatchType('Regular expression')

  expect(screen.queryByText('web01')).not.toBeInTheDocument()
})

test('a slow search cannot overwrite the result of a later one', async () => {
  const slow: Array<() => void> = []
  server.use(
    restApiHttp.post(SEARCH, async ({ request, response }) => {
      const body = (await request.json()) as SearchBody
      if (body.service_match.mode === 'exact') {
        await new Promise<void>((resolve) => slow.push(resolve))
        return response(200).json(searchResult([service('stale-host', 'HTTP request duration')]))
      }
      return response(200).json(searchResult([service('fresh-host', 'HTTP request duration')]))
    })
  )
  renderStep({ matchType: 'regex', servicePattern: 'HTTP request duration' })

  await pickMatchType('Exact match')
  await waitFor(() => expect(slow).toHaveLength(1))
  await pickMatchType('Regular expression')
  await waitFor(() => expect(screen.getByText('fresh-host')).toBeInTheDocument())

  slow.splice(0).forEach((resolve) => resolve())
  await settle()

  expect(screen.queryByText('stale-host')).not.toBeInTheDocument()
  expect(screen.getByText('fresh-host')).toBeInTheDocument()
})

test('a search still in flight is discarded once the service name is cleared', async () => {
  answer = searchResult([service('stale-host', 'HTTP request duration')])
  const search = heldExactSearch()
  const { model } = renderStep()

  model.value.servicePattern = 'HTTP request duration'
  await waitFor(() => expect(search.started()).toBe(true))

  model.value.servicePattern = ''
  search.release()
  await settle()

  expect(screen.queryByText('stale-host')).not.toBeInTheDocument()
  expect(screen.queryByText(/Matching services/)).not.toBeInTheDocument()
})

test('the conditions start at the Main folder, which applies to all hosts', async () => {
  renderStep()

  expect(screen.getByRole('heading', { name: 'Conditions' })).toBeVisible()
  await waitFor(() => expect(combobox('Folder')).toHaveTextContent('Main'))
})

test('choosing a folder narrows the conditions to it', async () => {
  const { model } = renderStep()

  void userEvent.click(combobox('Folder'))
  await userEvent.click(await screen.findByRole('option', { name: 'Main/Linux' }))

  expect(model.value.conditions.folder_path).toBe('option-linux')
})

test('a condition the form rejects blocks navigation and says why', async () => {
  answer = searchResult([service('web01', 'HTTP request duration')])
  const { navigation } = renderStep({
    servicePattern: 'HTTP request duration',
    conditions: { folder_path: MAIN_FOLDER, explicit_hosts: { value: [], negate: false } }
  })

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  expect(await screen.findByText('Please add at least one host.')).toBeVisible()
  expect(navigation.next).not.toHaveBeenCalled()
})

test('a host label group without labels blocks navigation like in the rule editor', async () => {
  answer = searchResult([service('web01', 'HTTP request duration')])
  const { navigation } = renderStep({
    servicePattern: 'HTTP request duration',
    conditions: {
      folder_path: MAIN_FOLDER,
      host_label_groups: [{ operator: 'and', label_group: [] }]
    }
  })

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  expect(await screen.findByText('Please add at least one host label.')).toBeVisible()
  expect(navigation.next).not.toHaveBeenCalled()
})

test('valid conditions let the step continue', async () => {
  answer = searchResult([service('web01', 'HTTP request duration')])
  const { navigation } = renderStep({
    servicePattern: 'HTTP request duration',
    conditions: { folder_path: MAIN_FOLDER, explicit_hosts: { value: ['web01'], negate: false } }
  })

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  await waitFor(() => expect(navigation.next).toHaveBeenCalled())
})

test('choosing a folder searches the matching services again, in that folder', async () => {
  answer = searchResult([service('web01', 'HTTP request duration')])
  renderStep()
  await pickServiceName('HTTP request duration')
  await waitFor(() => expect(screen.getByText('web01')).toBeInTheDocument())
  answer = searchResult([])

  void userEvent.click(combobox('Folder'))
  await userEvent.click(await screen.findByRole('option', { name: 'Main/Linux' }))

  await waitFor(() => {
    expect(screen.getByText(/No matching services/)).toBeInTheDocument()
  })
  expect(lastSearch?.conditions?.folder).toBe('/linux')
})
