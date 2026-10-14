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
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { afterEach, expect, test, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import NameAndServicesStep from '@/mode-alerts/steps/NameAndServicesStep.vue'
import { type AlertModel, emptyAlert } from '@/mode-alerts/types'

import { CONDITIONS_SPEC, FOLDER_PATHS, MAIN_FOLDER } from './conditions-spec'

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/service/collections/all`

// The services the endpoint reports for any search, so a test only has to say whether
// something matched.
let matching: Array<[string, string]> = []

function collection(services: Array<[string, string]>) {
  return {
    id: 'all',
    links: [],
    value: services.map(([hostName, serviceName]) => ({
      extensions: { host_name: hostName, description: serviceName }
    }))
  }
}

// The query of the latest search, to tell which conditions it applied.
let lastQuery: unknown = null

const server = useMswServer(
  http.post(ENDPOINT, async ({ request }) => {
    lastQuery = await request.json()
    return HttpResponse.json(collection(matching))
  })
)

afterEach(() => {
  cleanup()
  matching = []
  lastQuery = null
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
    components: { NameAndServicesStep },
    setup() {
      return { model, spec: CONDITIONS_SPEC, folderPaths: FOLDER_PATHS }
    },
    template: `<NameAndServicesStep v-model="model" :conditions-spec="spec" :folder-paths="folderPaths" :index="1" :is-completed="() => false" />`
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

// Only the step's own search matches exactly; the dropdown's suggestions always search.
function heldExactSearch(): { release: () => void; started: () => boolean } {
  const pending: Array<() => void> = []
  server.use(
    http.post(ENDPOINT, async ({ request }) => {
      if ((await exactMatchOn(request)) === true) {
        await new Promise<void>((resolve) => pending.push(resolve))
      }
      return HttpResponse.json(collection(matching))
    })
  )
  return {
    release: () => pending.splice(0).forEach((resolve) => resolve()),
    started: () => pending.length > 0
  }
}

async function exactMatchOn(request: Request): Promise<boolean> {
  const body = (await request.json()) as {
    query: { expr: Array<{ op: string; left: string }> }
  }
  return body.query.expr.find((condition) => condition.left === 'description')?.op === '='
}

test('choosing a service name lists the custom services it matches', async () => {
  matching = [
    ['web01', 'HTTP request duration'],
    ['web02', 'HTTP request duration']
  ]
  renderStep({ name: 'Latency too high' })

  await pickServiceName('HTTP request duration')

  await waitFor(() => {
    expect(screen.getByText('web01')).toBeInTheDocument()
  })
  expect(screen.getByText('web02')).toBeInTheDocument()
})

test('the discovered service names are offered as choices', async () => {
  matching = [
    ['web01', 'HTTP request duration'],
    ['web02', 'HTTP request duration'],
    ['db01', 'Query duration']
  ]
  renderStep({ name: 'Latency too high' })

  await open('Service name')

  expect(await screen.findByRole('option', { name: 'HTTP request duration' })).toBeInTheDocument()
  expect(screen.getByRole('option', { name: 'Query duration' })).toBeInTheDocument()
})

test('the number of matching services is reported', async () => {
  matching = [['web01', 'HTTP request duration']]
  renderStep({ name: 'Latency too high' })

  await pickServiceName('HTTP request duration')

  await waitFor(() => {
    expect(screen.getByText(/Matching services/)).toHaveTextContent('(1)')
  })
})

test('no results are shown before a search has run', () => {
  renderStep({ name: 'Latency too high', servicePattern: 'HTTP request duration' })

  expect(screen.queryByText(/Matching services/)).not.toBeInTheDocument()
})

test('errors are not shown before the first attempt to continue', () => {
  renderStep()

  expect(screen.queryByText('An alert name is required')).not.toBeInTheDocument()
})

test('a service name matching nothing says so without waiting for the next step', async () => {
  renderStep({ name: 'Latency too high' })

  await typeServiceName('nonexistent')

  await waitFor(() => {
    expect(screen.getByText(/No matching services/)).toBeInTheDocument()
  })
  expect(screen.queryByText(/Matching services/)).not.toBeInTheDocument()
})

test('a missing alert name blocks navigation with a required error', async () => {
  matching = [['web01', 'HTTP request duration']]
  const { navigation } = renderStep({ servicePattern: 'HTTP request duration' })

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  await waitFor(() => {
    expect(screen.getByText('An alert name is required')).toBeInTheDocument()
  })
  expect(navigation.next).not.toHaveBeenCalled()
})

test('a missing service name blocks navigation with a required error', async () => {
  const { navigation } = renderStep({ name: 'Latency too high' })

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  await waitFor(() => {
    expect(screen.getByText('A service name is required')).toBeInTheDocument()
  })
  expect(navigation.next).not.toHaveBeenCalled()
})

test('a service name matching nothing blocks navigation', async () => {
  const { navigation } = renderStep({ name: 'Latency too high', servicePattern: 'nonexistent' })

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  await waitFor(() => {
    expect(screen.getByText(/No matching services/)).toBeInTheDocument()
  })
  expect(navigation.next).not.toHaveBeenCalled()
})

test('an unparsable regular expression blocks navigation before any search', async () => {
  const { navigation } = renderStep({
    name: 'Latency too high',
    matchType: 'regex',
    servicePattern: '['
  })

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  await waitFor(() => {
    expect(screen.getByText('This is not a valid regular expression')).toBeInTheDocument()
  })
  expect(navigation.next).not.toHaveBeenCalled()
})

test.each([
  ['exact', 'TEST'],
  ['regex', 'duration']
] as const)(
  'a %s search matching nothing points at the discovery requirement',
  async (matchType, servicePattern) => {
    renderStep({ name: 'Latency too high', matchType, servicePattern })

    await userEvent.click(screen.getByRole('button', { name: /next step/i }))

    await waitFor(() => {
      expect(
        screen.getByText('No matching services. Only discovered services can be selected.')
      ).toBeInTheDocument()
    })
  }
)

test('the service name help explains both match types', async () => {
  renderStep()

  await userEvent.click(screen.getByRole('button', { name: 'How are service names matched?' }))

  const help = await screen.findByRole('tooltip')
  expect(help).toHaveTextContent(/Exact matching needs the complete service name/)
  expect(help).toHaveTextContent(/matches from the start of the service name/)
})

test('a named alert with at least one matching service continues to the next step', async () => {
  matching = [['web01', 'HTTP request duration']]
  const { navigation } = renderStep({
    name: 'Latency too high',
    servicePattern: 'HTTP request duration'
  })

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  await waitFor(() => {
    expect(navigation.next).toHaveBeenCalled()
  })
})

test('changing the match type discards the results of the previous search', async () => {
  matching = [['web01', 'HTTP request duration']]
  renderStep({ name: 'Latency too high' })

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
    http.post(ENDPOINT, async ({ request }) => {
      if ((await exactMatchOn(request)) === true) {
        await new Promise<void>((resolve) => slow.push(resolve))
        return HttpResponse.json(collection([['stale-host', 'HTTP request duration']]))
      }
      return HttpResponse.json(collection([['fresh-host', 'HTTP request duration']]))
    })
  )
  renderStep({
    name: 'Latency too high',
    matchType: 'regex',
    servicePattern: 'HTTP request duration'
  })

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
  matching = [['stale-host', 'HTTP request duration']]
  const search = heldExactSearch()
  const { model } = renderStep({ name: 'Latency too high' })

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
  matching = [['web01', 'HTTP request duration']]
  const { navigation } = renderStep({
    name: 'Latency too high',
    servicePattern: 'HTTP request duration',
    conditions: { folder_path: MAIN_FOLDER, explicit_hosts: { value: [], negate: false } }
  })

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  expect(await screen.findByText('Please add at least one host.')).toBeVisible()
  expect(navigation.next).not.toHaveBeenCalled()
})

test('a host label group without labels blocks navigation like in the rule editor', async () => {
  matching = [['web01', 'HTTP request duration']]
  const { navigation } = renderStep({
    name: 'Latency too high',
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
  matching = [['web01', 'HTTP request duration']]
  const { navigation } = renderStep({
    name: 'Latency too high',
    servicePattern: 'HTTP request duration',
    conditions: { folder_path: MAIN_FOLDER, explicit_hosts: { value: ['web01'], negate: false } }
  })

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  await waitFor(() => expect(navigation.next).toHaveBeenCalled())
})

test('choosing a folder searches the matching services again, in that folder', async () => {
  matching = [['web01', 'HTTP request duration']]
  renderStep({ name: 'Latency too high' })
  await pickServiceName('HTTP request duration')
  await waitFor(() => expect(screen.getByText('web01')).toBeInTheDocument())
  matching = []

  void userEvent.click(combobox('Folder'))
  await userEvent.click(await screen.findByRole('option', { name: 'Main/Linux' }))

  await waitFor(() => {
    expect(screen.getByText(/No matching services/)).toBeInTheDocument()
  })
  expect(JSON.stringify(lastQuery)).toContain('^/wato/linux/')
})
