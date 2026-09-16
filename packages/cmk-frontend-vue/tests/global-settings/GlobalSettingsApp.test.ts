/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import type {
  GlobalSettingsApp as GlobalSettingsAppData,
  GlobalSettingsOrigin,
  GlobalSettingsTopic
} from 'cmk-shared-typing/typescript/global_settings'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test, vi } from 'vitest'

import { initializeComponentRegistry } from '@/form/private/FormEditDispatcher/dispatch'

import GlobalSettingsApp from '@/global-settings/GlobalSettingsApp.vue'

initializeComponentRegistry()

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

const SETTING_URL = `${location.protocol}//${location.host}/api/internal/objects/global_setting/lock_on_logon_failures`
const BOOLEAN_SETTING_URL = `${location.protocol}//${location.host}/api/internal/objects/global_setting/site_piggyback_hub`
const SITE_SETTING_URL = `${location.protocol}//${location.host}/api/internal/objects/site_connection/remote_1/global_setting/lock_on_logon_failures`

const data: GlobalSettingsAppData = {
  title: 'Global settings',
  breadcrumb: [
    { title: 'Setup', link: null },
    { title: 'Global settings', link: null }
  ],
  scope: { type: 'global' },
  topics: [
    {
      icon: 'users',
      headline: 'User management',
      subline: 'Configures user/authentication settings',
      warning: null,
      variables: [
        {
          name: 'lock_on_logon_failures',
          spec: {
            type: 'integer',
            title: 'Lock user accounts after N login failures',
            help: '',
            validators: [],
            label: null,
            unit: null,
            input_hint: null
          },
          value: 10,
          default_value: 10,
          global_value: null,
          origin: 'factory',
          site_overrides: [],
          hints: []
        }
      ]
    }
  ]
}

const booleanTopic: GlobalSettingsTopic = {
  icon: 'sites',
  headline: 'Distributed monitoring',
  subline: 'Configures distribution settings',
  warning: null,
  variables: [
    {
      name: 'site_piggyback_hub',
      spec: {
        type: 'boolean_choice',
        title: 'Enable piggyback-hub',
        help: '',
        validators: [],
        label: null,
        text_on: 'on',
        text_off: 'off'
      },
      value: false,
      default_value: false,
      global_value: null,
      origin: 'factory',
      site_overrides: [],
      hints: []
    }
  ]
}

const resettableTopic: GlobalSettingsTopic = {
  icon: 'users',
  headline: 'Resettable settings',
  subline: 'Everything in here was modified',
  warning: null,
  variables: [
    { ...data.topics[0]!.variables[0]!, origin: 'global' },
    { ...booleanTopic.variables[0]!, value: true, origin: 'global' }
  ]
}

const overriddenTopic: GlobalSettingsTopic = {
  ...data.topics[0]!,
  variables: [
    {
      ...data.topics[0]!.variables[0]!,
      site_overrides: [
        {
          site_id: 'remote_1',
          title: 'Remote site 1',
          url: '/remote_1/check_mk/site_specific_settings.py?site=remote_1'
        }
      ]
    }
  ]
}

const siteMixedTopic: GlobalSettingsTopic = {
  ...resettableTopic,
  variables: [
    { ...resettableTopic.variables[0]!, global_value: 15 },
    { ...resettableTopic.variables[1]!, origin: 'site', global_value: false }
  ]
}

interface Recorded {
  method: string
  ifMatch: string | null
  body: unknown
}
let requests: Recorded[] = []
let serverValue: { value: number; origin: GlobalSettingsOrigin } = {
  value: 15,
  origin: 'global'
}
let booleanServerValue: { value: boolean; origin: GlobalSettingsOrigin } = {
  value: false,
  origin: 'factory'
}

const server = setupServer(
  http.get(SETTING_URL, () => {
    requests.push({ method: 'GET', ifMatch: null, body: null })
    return HttpResponse.json(
      { varname: 'lock_on_logon_failures', ...serverValue },
      { headers: { ETag: '"v1"' } }
    )
  }),
  http.put(SETTING_URL, async ({ request }) => {
    const body = (await request.json()) as { value: number }
    requests.push({ method: 'PUT', ifMatch: request.headers.get('If-Match'), body })
    serverValue = { value: body.value, origin: 'global' }
    return HttpResponse.json(
      { varname: 'lock_on_logon_failures', ...serverValue },
      { headers: { ETag: '"v2"' } }
    )
  }),
  http.delete(SETTING_URL, ({ request }) => {
    requests.push({ method: 'DELETE', ifMatch: request.headers.get('If-Match'), body: null })
    serverValue = { value: 10, origin: 'factory' }
    return new HttpResponse(null, { status: 204 })
  }),
  http.put(BOOLEAN_SETTING_URL, async ({ request }) => {
    const body = (await request.json()) as { value: boolean }
    requests.push({ method: 'PUT', ifMatch: request.headers.get('If-Match'), body })
    booleanServerValue = { value: body.value, origin: 'global' }
    return HttpResponse.json(
      { varname: 'site_piggyback_hub', ...booleanServerValue },
      { headers: { ETag: '"b2"' } }
    )
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  requests = []
  serverValue = { value: 15, origin: 'global' }
  booleanServerValue = { value: false, origin: 'factory' }
  server.resetHandlers()
})
afterAll(() => server.close())

async function openEditor() {
  render(GlobalSettingsApp, { props: data })
  await userEvent.click(
    screen.getByRole('button', { name: 'Toggle accordion item User management' })
  )
  await userEvent.click(
    await screen.findByRole('button', { name: 'Edit Lock user accounts after N login failures' })
  )
  await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET']))
}

async function openSiteEditor(origin: GlobalSettingsOrigin): Promise<HTMLElement> {
  server.use(
    http.get(SITE_SETTING_URL, () =>
      HttpResponse.json(
        { varname: 'lock_on_logon_failures', value: 20, origin },
        { headers: { ETag: '"s1"' } }
      )
    )
  )
  render(GlobalSettingsApp, {
    props: { ...data, scope: { type: 'site', site_id: 'remote_1' }, topics: [siteMixedTopic] }
  })
  await userEvent.click(
    screen.getByRole('button', { name: 'Toggle accordion item Resettable settings' })
  )
  await userEvent.click(
    await screen.findByRole('button', { name: 'Edit Lock user accounts after N login failures' })
  )
  return await screen.findByRole('dialog')
}

function settingRow() {
  return screen
    .getByRole('button', { name: 'Edit Lock user accounts after N login failures' })
    .closest('.global-settings-variable-row')
}

// Scoped to the topic, because the permanent work-in-progress notice is an alert as well.
function topic(headline: string): HTMLElement {
  const element = screen
    .getByRole('button', { name: `Toggle accordion item ${headline}` })
    .closest<HTMLElement>('.cmk-accordion-item')
  if (element === null) {
    throw new Error(`No accordion item found for the topic "${headline}"`)
  }
  return element
}

const secondTopic: GlobalSettingsTopic = {
  icon: 'sites',
  headline: 'Site management',
  subline: 'Configures site settings',
  warning: null,
  variables: [
    {
      ...data.topics[0]!.variables[0]!,
      name: 'site_setting',
      spec: { ...data.topics[0]!.variables[0]!.spec, title: 'Site setting' },
      origin: 'global'
    }
  ]
}

const warnedTopic: GlobalSettingsTopic = {
  ...data.topics[0]!,
  headline: 'Developer tools',
  subline: 'Settings for developing Checkmk',
  warning: 'These settings are internal and unsupported.'
}
//
// The app reads and writes `?search=`, shared by every test in this file.
beforeEach(() => {
  window.history.replaceState({}, '', '/')
})

describe('GlobalSettingsApp page header', () => {
  test('renders the breadcrumb of the page', () => {
    render(GlobalSettingsApp, { props: data })

    expect(screen.getByText('Setup')).toBeInTheDocument()
    expect(screen.getByText('Global settings')).toBeInTheDocument()
  })

  test('renders the work in progress notice', () => {
    render(GlobalSettingsApp, { props: data })

    expect(
      screen.getByText('This page is work in progress. It shows a subset of the global settings.')
    ).toBeInTheDocument()
  })
})

describe('GlobalSettingsApp accordion', () => {
  test('all topics start collapsed and the toggle expands and collapses them all', async () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [...data.topics, secondTopic] } })
    expect(screen.queryByText('Site setting')).not.toBeInTheDocument()
    expect(screen.queryByText('Lock user accounts after N login failures')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Expand all' }))
    expect(screen.getByText('Site setting')).toBeInTheDocument()
    expect(screen.getByText('Lock user accounts after N login failures')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Collapse all' }))
    expect(screen.queryByText('Site setting')).not.toBeInTheDocument()
  })

  test('the topic header counts the modified variables', () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [secondTopic] } })
    expect(screen.getByText('1 modified')).toBeInTheDocument()
  })

  test('a topic without a single modification carries no tag', () => {
    render(GlobalSettingsApp, { props: data })
    expect(screen.queryByText(/\d+ modified/)).not.toBeInTheDocument()
  })

  test('tabbing through expanded topics reaches each tag and edit button', async () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [...data.topics, secondTopic] } })
    await userEvent.click(screen.getByRole('button', { name: 'Expand all' }))
    screen.getByRole('button', { name: 'Toggle accordion item User management' }).focus()

    await userEvent.tab()
    expect(
      screen.getByRole('button', { name: 'Edit Lock user accounts after N login failures' })
    ).toHaveFocus()
    await userEvent.tab()
    expect(
      screen.getByRole('button', { name: 'Toggle accordion item Site management' })
    ).toHaveFocus()
    await userEvent.tab()
    expect(screen.getByRole('button', { name: '1 modified' })).toHaveFocus()
    await userEvent.tab()
    expect(screen.getByRole('button', { name: 'Edit Site setting' })).toHaveFocus()
  })

  test('only modified rows are marked', async () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [...data.topics, secondTopic] } })
    await userEvent.click(screen.getByRole('button', { name: 'Expand all' }))
    expect(screen.getAllByText('(modified)')).toHaveLength(1)
    expect(
      screen.getByText('Site setting').closest('.global-settings-variable-row')
    ).toHaveTextContent('(modified)')
  })
})

describe('GlobalSettingsApp', () => {
  test('the editor is titled as editing a global setting', async () => {
    await openEditor()
    expect(screen.getByRole('dialog', { name: /^Edit global setting/ })).toBeInTheDocument()
  })

  test('opening the editor with the keyboard moves focus into it', async () => {
    render(GlobalSettingsApp, { props: data })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item User management' })
    )
    screen.getByRole('button', { name: 'Edit Lock user accounts after N login failures' }).focus()
    await userEvent.keyboard('{Enter}')

    await screen.findByRole('dialog')
    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Edit global setting' })).toHaveFocus()
    )
  })

  test.each([
    { closing: 'Escape', close: async () => userEvent.keyboard('{Escape}') },
    {
      closing: 'Cancel',
      close: async () =>
        userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' }))
    },
    {
      closing: 'Save',
      close: async () => userEvent.click(screen.getByRole('button', { name: 'Save' }))
    }
  ])('closing the editor with $closing returns focus to the edit button', async ({ close }) => {
    render(GlobalSettingsApp, { props: data })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item User management' })
    )
    const editButton = screen.getByRole('button', {
      name: 'Edit Lock user accounts after N login failures'
    })
    editButton.focus()
    await userEvent.keyboard('{Enter}')
    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET']))
    await waitFor(() => expect(editButton).not.toHaveFocus())

    await close()

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(editButton).toHaveFocus()
  })

  test('opening the editor loads the server value and refreshes the row', async () => {
    await openEditor()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('(modified)')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(15))
  })

  test('saving an untouched editor stores the loaded effective value, not the rendered one', async () => {
    await openEditor()
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET', 'PUT']))
    expect(requests[1]).toMatchObject({ ifMatch: '"v1"', body: { value: 15 } })
  })

  test('the editor shows the factory value and the overriding sites alongside the current one', async () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [overriddenTopic] } })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item User management' })
    )
    await userEvent.click(
      await screen.findByRole('button', { name: 'Edit Lock user accounts after N login failures' })
    )
    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET']))

    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText('Factory setting')).toBeInTheDocument()
    expect(within(dialog).getByText('10')).toBeInTheDocument()
    expect(within(dialog).getByText('This variable has been modified.')).toBeInTheDocument()

    expect(within(dialog).getByText('Remote site 1')).toBeVisible()
    expect(within(dialog).getByRole('link', { name: 'Open site settings' })).toHaveAttribute(
      'href',
      '/remote_1/check_mk/site_specific_settings.py?site=remote_1'
    )
  })

  test('saving sends the edited value guarded by the loaded etag', async () => {
    await openEditor()
    await fireEvent.update(await screen.findByRole('spinbutton'), '20')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET', 'PUT']))
    expect(requests[1]).toMatchObject({ ifMatch: '"v1"', body: { value: 20 } })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.getByText('20')).toBeInTheDocument()
  })

  test('resetting deletes the explicit value and shows the factory default afterwards', async () => {
    await openEditor()
    await waitFor(() => expect(screen.getByText('15')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: /Remove modification/ }))
    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByRole('alert')).toHaveTextContent(
      'The configured value will be discarded and the factory default will be used instead.'
    )
    await userEvent.click(within(dialog).getByRole('button', { name: 'Remove' }))

    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET', 'DELETE', 'GET']))
    expect(requests[1]!.ifMatch).toBe('"v1"')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.queryByText('(modified)')).not.toBeInTheDocument()
    const row = settingRow()
    expect(row).not.toHaveTextContent('15')
    expect(row).toHaveTextContent('10')
  })

  test('saving a value equal to the factory default still marks the row as explicitly set', async () => {
    await openEditor()
    await fireEvent.update(await screen.findByRole('spinbutton'), '10')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET', 'PUT']))
    expect(requests[1]).toMatchObject({ ifMatch: '"v1"', body: { value: 10 } })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.getByText('(modified)')).toBeInTheDocument()
  })

  test('an explicit value equal to the factory default gets the explicit-setting wording', async () => {
    serverValue = { value: 10, origin: 'global' }
    await openEditor()
    const dialog = screen.getByRole('dialog')
    const removeButton = await within(dialog).findByRole('button', {
      name: 'Remove explicit setting'
    })
    expect(
      within(dialog).getByText(
        'This setting uses an explicit value and overrides the factory and Global settings value.'
      )
    ).toBeInTheDocument()

    await userEvent.click(removeButton)
    expect(within(dialog).getByText('Remove explicit setting?')).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Remove' }))

    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET', 'DELETE', 'GET']))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.queryByText('(modified)')).not.toBeInTheDocument()
  })

  test('toggling a boolean setting saves the flipped value inline without a dialog', async () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [booleanTopic] } })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item Distributed monitoring' })
    )
    const inlineSwitch = screen.getByRole('switch', { name: 'Toggle Enable piggyback-hub' })
    expect(inlineSwitch).toHaveAttribute('aria-checked', 'false')

    await userEvent.click(inlineSwitch)

    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['PUT']))
    expect(requests[0]).toMatchObject({ ifMatch: '*', body: { value: true } })
    await waitFor(() => expect(inlineSwitch).toHaveAttribute('aria-checked', 'true'))
    expect(screen.getByText('(modified)')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  test('the inline switch toggles with Enter and Space and keeps focus', async () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [booleanTopic] } })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item Distributed monitoring' })
    )
    const inlineSwitch = screen.getByRole('switch', { name: 'Toggle Enable piggyback-hub' })
    inlineSwitch.focus()

    await userEvent.keyboard('{Enter}')
    await waitFor(() => expect(inlineSwitch).toHaveAttribute('aria-checked', 'true'))

    await userEvent.keyboard(' ')
    await waitFor(() => expect(inlineSwitch).toHaveAttribute('aria-checked', 'false'))

    expect(requests.map((r) => r.method)).toEqual(['PUT', 'PUT'])
    expect(inlineSwitch).toHaveFocus()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  test('a rejected toggle keeps the shown value and reports the server message on the row', async () => {
    server.use(
      http.put(BOOLEAN_SETTING_URL, () =>
        HttpResponse.json(
          { title: 'Precondition failed', detail: 'ETag mismatch' },
          { status: 412 }
        )
      )
    )
    render(GlobalSettingsApp, { props: { ...data, topics: [booleanTopic] } })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item Distributed monitoring' })
    )
    const inlineSwitch = screen.getByRole('switch', { name: 'Toggle Enable piggyback-hub' })

    await userEvent.click(inlineSwitch)

    expect(await screen.findByText(/ETag mismatch/)).toBeInTheDocument()
    expect(inlineSwitch).toHaveAttribute('aria-checked', 'false')
    expect(screen.queryByText('(modified)')).not.toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  test('a rejected toggle announces the server message as an alert', async () => {
    server.use(
      http.put(BOOLEAN_SETTING_URL, () =>
        HttpResponse.json(
          { title: 'Precondition failed', detail: 'ETag mismatch' },
          { status: 412 }
        )
      )
    )
    render(GlobalSettingsApp, { props: { ...data, topics: [booleanTopic] } })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item Distributed monitoring' })
    )
    const inlineSwitch = screen.getByRole('switch', { name: 'Toggle Enable piggyback-hub' })
    inlineSwitch.focus()
    await userEvent.keyboard(' ')

    expect(await within(topic('Distributed monitoring')).findByRole('alert')).toHaveTextContent(
      /ETag mismatch/
    )
    expect(inlineSwitch).toHaveFocus()
  })

  test('a rejected save keeps the editor open and shows the server message', async () => {
    server.use(
      http.put(SETTING_URL, () =>
        HttpResponse.json(
          { title: 'Precondition failed', detail: 'ETag mismatch' },
          { status: 412 }
        )
      )
    )
    await openEditor()
    await userEvent.click(await screen.findByRole('button', { name: 'Save' }))

    expect(await screen.findByText(/ETag mismatch/)).toBeInTheDocument()
    expect(screen.getByText('Saving failed')).toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  test('a value the server rejects as invalid is reported in the editor and not stored', async () => {
    server.use(
      http.put(SETTING_URL, async ({ request }) => {
        requests.push({
          method: 'PUT',
          ifMatch: request.headers.get('If-Match'),
          body: await request.json()
        })
        return HttpResponse.json(
          { title: 'Problem in field ', detail: 'The value must be at least 1.' },
          { status: 400 }
        )
      })
    )
    await openEditor()
    await waitFor(() => expect(screen.getByText('15')).toBeInTheDocument())
    await fireEvent.update(await screen.findByRole('spinbutton'), '0')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText(/The value must be at least 1\./)).toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET', 'PUT']))
    const row = settingRow()
    expect(row).toHaveTextContent('15')
    expect(row).not.toHaveTextContent('0')
  })

  test('cancelling the editor discards the edit without saving', async () => {
    await openEditor()
    await waitFor(() => expect(screen.getByText('15')).toBeInTheDocument())
    await fireEvent.update(await screen.findByRole('spinbutton'), '20')
    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' })
    )

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(requests.map((r) => r.method)).toEqual(['GET'])
    const row = settingRow()
    expect(row).toHaveTextContent('15')
    expect(row).not.toHaveTextContent('20')
  })

  test('Escape closes the editor and discards the edit without saving', async () => {
    await openEditor()
    await waitFor(() => expect(screen.getByText('15')).toBeInTheDocument())
    await fireEvent.update(await screen.findByRole('spinbutton'), '20')
    await userEvent.keyboard('{Escape}')

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(requests.map((r) => r.method)).toEqual(['GET'])
    const row = settingRow()
    expect(row).toHaveTextContent('15')
    expect(row).not.toHaveTextContent('20')
  })

  test('a failed load shows a loading error and keeps saving disabled', async () => {
    server.use(
      http.get(SETTING_URL, () =>
        HttpResponse.json({ title: 'Not found', detail: 'No such variable' }, { status: 404 })
      )
    )
    render(GlobalSettingsApp, { props: data })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item User management' })
    )
    await userEvent.click(
      await screen.findByRole('button', { name: 'Edit Lock user accounts after N login failures' })
    )

    expect(await screen.findByText(/No such variable/)).toBeInTheDocument()
    expect(screen.getByText('Loading failed')).toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()
  })

  test('a site scope routes load and save through the site connection endpoints', async () => {
    server.use(
      http.get(SITE_SETTING_URL, () => {
        requests.push({ method: 'GET', ifMatch: null, body: null })
        return HttpResponse.json(
          { varname: 'lock_on_logon_failures', value: 15, origin: 'site' },
          { headers: { ETag: '"s1"' } }
        )
      }),
      http.put(SITE_SETTING_URL, async ({ request }) => {
        requests.push({
          method: 'PUT',
          ifMatch: request.headers.get('If-Match'),
          body: await request.json()
        })
        return HttpResponse.json(
          { varname: 'lock_on_logon_failures', value: 20, origin: 'site' },
          { headers: { ETag: '"s2"' } }
        )
      })
    )
    render(GlobalSettingsApp, {
      props: { ...data, scope: { type: 'site', site_id: 'remote_1' } }
    })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item User management' })
    )
    await userEvent.click(
      await screen.findByRole('button', { name: 'Edit Lock user accounts after N login failures' })
    )
    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET']))
    await fireEvent.update(await screen.findByRole('spinbutton'), '20')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET', 'PUT']))
    expect(requests[1]).toMatchObject({ ifMatch: '"s1"', body: { value: 20 } })
  })

  test('the global page counts the variables that a site overrides', () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [overriddenTopic] } })

    expect(screen.getByText('1 overridden on sites')).toBeInTheDocument()
  })

  test('a site page counts a value modified in the global settings as modified', () => {
    render(GlobalSettingsApp, {
      props: { ...data, scope: { type: 'site', site_id: 'remote_1' }, topics: [resettableTopic] }
    })

    expect(screen.getByText('2 modified')).toBeInTheDocument()
    expect(screen.queryByText(/overridden on this site/)).not.toBeInTheDocument()
  })

  test('a site page tags the values it overrides itself apart from the modified ones', () => {
    render(GlobalSettingsApp, {
      props: { ...data, scope: { type: 'site', site_id: 'remote_1' }, topics: [siteMixedTopic] }
    })

    expect(screen.getByText('2 modified')).toBeInTheDocument()
    expect(screen.getByText('1 overridden on this site')).toBeInTheDocument()
  })

  test('a site editor shows the inherited value and the state of the shown one', async () => {
    const dialog = await openSiteEditor('site')

    expect(await within(dialog).findByText('Global settings')).toBeInTheDocument()
    expect(within(dialog).getByText('15')).toBeInTheDocument()
    expect(
      within(dialog).getByText('This variable is overridden on this site.')
    ).toBeInTheDocument()
  })

  test('a site editor names the global settings as the source of an inherited value', async () => {
    const dialog = await openSiteEditor('global')

    expect(
      await within(dialog).findByText('This variable inherits the value from Global settings.')
    ).toBeInTheDocument()
    expect(
      within(dialog).queryByRole('button', { name: 'Remove site-specific value' })
    ).not.toBeInTheDocument()
  })

  test('removing a site override warns that the global settings take over', async () => {
    const dialog = await openSiteEditor('site')
    await userEvent.click(
      await within(dialog).findByRole('button', { name: 'Remove site-specific value' })
    )

    expect(
      within(dialog).getByText('The site will inherit the value from Global settings.')
    ).toBeInTheDocument()
  })

  test('the global editor has no section for an inherited value', async () => {
    await openEditor()

    expect(
      within(screen.getByRole('dialog')).queryByText('Global settings')
    ).not.toBeInTheDocument()
  })

  test('a load response arriving after its editor was closed does not leak into the next editor', async () => {
    const secondSettingUrl = `${location.protocol}//${location.host}/api/internal/objects/global_setting/site_setting`
    let releaseStaleLoad: () => void = () => {}
    const staleLoad = new Promise<void>((resolve) => {
      releaseStaleLoad = resolve
    })
    let putIfMatch: string | null = null
    server.use(
      http.get(SETTING_URL, async () => {
        await staleLoad
        return HttpResponse.json(
          { varname: 'lock_on_logon_failures', value: 99, origin: 'global' },
          { headers: { ETag: '"stale"' } }
        )
      }),
      http.get(secondSettingUrl, () =>
        HttpResponse.json(
          { varname: 'site_setting', value: 42, origin: 'global' },
          { headers: { ETag: '"fresh"' } }
        )
      ),
      http.put(secondSettingUrl, ({ request }) => {
        putIfMatch = request.headers.get('If-Match')
        return HttpResponse.json(
          { varname: 'site_setting', value: 43, origin: 'global' },
          { headers: { ETag: '"fresh2"' } }
        )
      })
    )
    render(GlobalSettingsApp, { props: { ...data, topics: [...data.topics, secondTopic] } })
    await userEvent.click(screen.getByRole('button', { name: 'Expand all' }))
    await userEvent.click(
      screen.getByRole('button', { name: 'Edit Lock user accounts after N login failures' })
    )
    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' })
    )
    await userEvent.click(screen.getByRole('button', { name: 'Edit Site setting' }))
    await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(42))

    releaseStaleLoad()
    await waitFor(() => expect(screen.getByText('99')).toBeInTheDocument())

    await fireEvent.update(screen.getByRole('spinbutton'), '43')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(putIfMatch).toBe('"fresh"'))
    expect(screen.queryByText('Loading failed')).not.toBeInTheDocument()
  })
})

describe('GlobalSettingsApp deep link', () => {
  function deepLink(varname: string): void {
    window.history.replaceState({}, '', `/?varname=${varname}`)
    render(GlobalSettingsApp, { props: data })
  }

  test('a setting named in the URL opens its topic and its editor', async () => {
    deepLink('lock_on_logon_failures')

    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET']))
    expect(
      screen.getByRole('button', { name: 'Edit Lock user accounts after N login failures' })
    ).toBeInTheDocument()
  })

  test('a setting the page does not show is ignored', async () => {
    deepLink('no_such_setting')

    await waitFor(() => expect(requests).toEqual([]))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  test('opening a setting names it in the URL', async () => {
    await openEditor()

    await waitFor(() => expect(window.location.search).toBe('?varname=lock_on_logon_failures'))
  })

  test('closing the editor drops the setting from the URL', async () => {
    deepLink('lock_on_logon_failures')
    await screen.findByRole('dialog')

    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' })
    )

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(window.location.search).toBe('')
  })
})

describe('GlobalSettingsApp hints', () => {
  const hintedTopic: GlobalSettingsTopic = {
    ...data.topics[0]!,
    headline: 'Hinted settings',
    variables: [
      {
        ...data.topics[0]!.variables[0]!,
        hints: [
          { text: 'A full restart is <b>required</b>.', variant: 'warning', copyable: null },
          {
            text: 'Reachable at ',
            variant: 'info',
            copyable: 'http://localhost/heute/check_mk/mcp'
          }
        ]
      }
    ]
  }

  async function openHintedEditor(): Promise<HTMLElement> {
    render(GlobalSettingsApp, { props: { ...data, topics: [hintedTopic] } })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item Hinted settings' })
    )
    await userEvent.click(
      await screen.findByRole('button', { name: 'Edit Lock user accounts after N login failures' })
    )
    return await screen.findByRole('dialog')
  }

  test('each hint is shown in a box matching its variant', async () => {
    const dialog = await openHintedEditor()

    expect(within(dialog).getByRole('alert')).toHaveTextContent('A full restart is required.')
    expect(within(dialog).getByRole('status')).toHaveTextContent('Reachable at')
  })

  test('a copyable hint shows its value next to a copy control', async () => {
    const dialog = await openHintedEditor()

    expect(within(dialog).getByText('http://localhost/heute/check_mk/mcp')).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Copy to clipboard' })).toBeInTheDocument()
  })
})

describe('GlobalSettingsApp overview presentation', () => {
  test('every topic is listed with its headline and subline, and expanding one reveals only its own settings', async () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [...data.topics, secondTopic] } })

    expect(screen.getByText('Configures user/authentication settings')).toBeInTheDocument()
    expect(screen.getByText('Configures site settings')).toBeInTheDocument()

    await userEvent.click(
      screen.getByRole('button', { name: /Toggle accordion item User management/ })
    )

    expect(screen.getByText('Lock user accounts after N login failures')).toBeInTheDocument()
    expect(screen.queryByText('Site setting')).not.toBeInTheDocument()
  })

  test("a row shows the setting's title and the value in force", async () => {
    render(GlobalSettingsApp, { props: data })
    await userEvent.click(screen.getByRole('button', { name: 'Expand all' }))

    const row = screen
      .getByText('Lock user accounts after N login failures')
      .closest('.global-settings-variable-row')

    expect(row).toHaveTextContent('10')
  })

  test("a topic's warning is shown above its settings", async () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [warnedTopic] } })
    await userEvent.click(screen.getByRole('button', { name: 'Expand all' }))

    expect(within(topic(warnedTopic.headline)).getByRole('alert')).toHaveTextContent(
      'These settings are internal and unsupported.'
    )
  })

  test('a topic without a warning renders no warning at all', async () => {
    render(GlobalSettingsApp, { props: data })
    await userEvent.click(screen.getByRole('button', { name: 'Expand all' }))

    expect(within(topic(data.topics[0]!.headline)).queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('GlobalSettingsApp search', () => {
  const secondVariable = {
    ...data.topics[0]!.variables[0]!,
    name: 'user_idle_timeout',
    spec: { ...data.topics[0]!.variables[0]!.spec, title: 'Login session idle timeout' }
  }
  const searchData: GlobalSettingsAppData = {
    ...data,
    topics: [
      { ...data.topics[0]!, variables: [...data.topics[0]!.variables, secondVariable] },
      secondTopic
    ]
  }

  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  function setup(props: GlobalSettingsAppData = searchData) {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(GlobalSettingsApp, { props })
    return user
  }

  async function search(user: ReturnType<typeof setup>, query: string) {
    await user.type(screen.getByRole('searchbox'), query)
    // Past the filter debounce.
    await vi.advanceTimersByTimeAsync(200)
  }

  // Highlighting splits the text around a <mark>, which getByText does not see.
  const label = (text: string) => (_content: string, element: Element | null) =>
    element?.tagName === 'SPAN' && element.textContent?.trim() === text

  test('a query matching one variable hides the topics without a hit', async () => {
    const user = setup()
    await search(user, 'Site setting')

    expect(screen.getByText(label('Site setting'))).toBeInTheDocument()
    expect(screen.queryByText(label('User management'))).not.toBeInTheDocument()
  })

  test('a query matching only the topic headline finds nothing', async () => {
    const user = setup()
    await search(user, 'Site management')

    expect(screen.getByText('No matching settings found.')).toBeInTheDocument()
  })

  test('a query matching one variable title hides its siblings in the same topic', async () => {
    const user = setup()
    await search(user, 'idle timeout')

    expect(screen.getByText(label('Login session idle timeout'))).toBeInTheDocument()
    expect(
      screen.queryByText(label('Lock user accounts after N login failures'))
    ).not.toBeInTheDocument()
  })

  test('a matching section starts open and can be collapsed again', async () => {
    const user = setup()
    await search(user, 'idle')
    expect(screen.getByText(label('Login session idle timeout'))).toBeInTheDocument()

    await user.click(screen.getByText(label('User management')))
    expect(screen.queryByText(label('Login session idle timeout'))).not.toBeInTheDocument()
  })

  test('changing the query reopens the matching sections', async () => {
    const user = setup()
    await search(user, 'idle')
    await user.click(screen.getByText(label('User management')))
    expect(screen.queryByText(label('Login session idle timeout'))).not.toBeInTheDocument()

    await search(user, ' timeout')
    expect(screen.getByText(label('Login session idle timeout'))).toBeInTheDocument()
  })

  test('ending the search collapses every section', async () => {
    const user = setup()
    await search(user, 'idle')
    expect(screen.getByText(label('Login session idle timeout'))).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Clear search' }))
    await vi.advanceTimersByTimeAsync(200)
    expect(screen.queryByText(label('Login session idle timeout'))).not.toBeInTheDocument()
    expect(
      screen.queryByText(label('Lock user accounts after N login failures'))
    ).not.toBeInTheDocument()
  })

  test('a query without any match shows the empty state, whose reset button clears it', async () => {
    const user = setup()
    await search(user, 'no such setting')

    expect(screen.getByText('No matching settings found.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reset search' }))
    await vi.advanceTimersByTimeAsync(200)
    expect(screen.queryByText('No matching settings found.')).not.toBeInTheDocument()
    expect(screen.getByRole('searchbox')).toHaveValue('')
  })

  test('the matched substring is marked in a variable title', async () => {
    const user = setup()
    await search(user, 'idle timeout')

    expect(
      screen.getByText(label('Login session idle timeout')).querySelector('mark')
    ).toHaveTextContent('idle timeout')
  })

  test('the expand/collapse toggle keeps working while a search is active', async () => {
    const user = setup()
    await search(user, 'idle')

    await user.click(screen.getByRole('button', { name: 'Collapse all' }))
    expect(screen.queryByText(label('Login session idle timeout'))).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Expand all' }))
    expect(screen.getByText(label('Login session idle timeout'))).toBeInTheDocument()
  })

  test('the topic header counts stay totals while a search filters the rows', async () => {
    const user = setup({ ...data, topics: [resettableTopic] })
    await search(user, 'piggyback')

    expect(screen.getByText(label('Enable piggyback-hub'))).toBeInTheDocument()
    expect(screen.getByText('2 modified')).toBeInTheDocument()
  })

  test('a value changed while a search is active persists after the query is cleared', async () => {
    const user = setup({ ...data, topics: [data.topics[0]!, booleanTopic] })
    await search(user, 'piggyback')

    await user.click(screen.getByRole('switch', { name: 'Toggle Enable piggyback-hub' }))
    await vi.advanceTimersByTimeAsync(200)
    expect(screen.getByRole('switch', { name: 'Toggle Enable piggyback-hub' })).toHaveAttribute(
      'aria-checked',
      'true'
    )

    await user.click(screen.getByRole('button', { name: 'Clear search' }))
    await vi.advanceTimersByTimeAsync(200)
    // The topic was only open because the search forced it open.
    await user.click(screen.getByRole('button', { name: 'Expand all' }))

    const row = screen
      .getByText(label('Enable piggyback-hub'))
      .closest('.global-settings-variable-row')
    expect(row).toHaveTextContent('(modified)')
    expect(screen.getByRole('switch', { name: 'Toggle Enable piggyback-hub' })).toHaveAttribute(
      'aria-checked',
      'true'
    )
  })

  describe('modification filter', () => {
    async function filterBy(user: ReturnType<typeof setup>, label: string) {
      await user.click(screen.getByRole('button', { name: `Toggle ${label}` }))
    }

    const mixedTopic: GlobalSettingsTopic = {
      ...searchData.topics[0]!,
      variables: [searchData.topics[0]!.variables[0]!, { ...secondVariable, origin: 'global' }]
    }

    test('modified only hides the rows that still use their default', async () => {
      const user = setup()
      await filterBy(user, 'Modified only')
      await user.click(screen.getByRole('button', { name: 'Expand all' }))

      expect(screen.getByText(label('Site setting'))).toBeInTheDocument()
      expect(screen.queryByText(label('Login session idle timeout'))).not.toBeInTheDocument()
    })

    test('the site override filter stays away while nothing is overridden', () => {
      setup()

      expect(
        screen.queryByRole('button', { name: 'Toggle Site overrides only' })
      ).not.toBeInTheDocument()
    })

    test('a site override filter in the URL is ignored while nothing is overridden', () => {
      window.history.replaceState({}, '', '/?filter=site')
      setup()

      expect(screen.getByText(label('Site management'))).toBeInTheDocument()
      expect(screen.getByText(label('User management'))).toBeInTheDocument()
    })

    test('site overrides only keeps the variables a site overrides on the global page', async () => {
      const user = setup({ ...searchData, topics: [overriddenTopic, secondTopic] })
      await filterBy(user, 'Site overrides only')
      await user.click(screen.getByRole('button', { name: 'Expand all' }))

      expect(
        screen.getByText(label('Lock user accounts after N login failures'))
      ).toBeInTheDocument()
      expect(screen.queryByText(label('Site setting'))).not.toBeInTheDocument()
    })

    test('site overrides only hides everything the site does not override itself', async () => {
      const user = setup({
        ...searchData,
        scope: { type: 'site', site_id: 'remote_1' },
        topics: [siteMixedTopic]
      })
      await filterBy(user, 'Site overrides only')
      await user.click(screen.getByRole('button', { name: 'Expand all' }))

      expect(screen.getByText(label('Enable piggyback-hub'))).toBeInTheDocument()
      expect(
        screen.queryByText(label('Lock user accounts after N login failures'))
      ).not.toBeInTheDocument()
    })

    test('the filter leaves the sections closed', async () => {
      const user = setup()
      await filterBy(user, 'Modified only')

      expect(screen.getByText(label('Site management'))).toBeInTheDocument()
      expect(screen.queryByText(label('Site setting'))).not.toBeInTheDocument()
    })

    test('the filter narrows the search result', async () => {
      const user = setup()
      await search(user, 'idle')
      expect(screen.getByText(label('Login session idle timeout'))).toBeInTheDocument()

      await filterBy(user, 'Modified only')
      expect(screen.getByText('No matching settings found.')).toBeInTheDocument()
    })

    test('a filter in the URL pre-applies on mount', () => {
      window.history.replaceState({}, '', '/?filter=modified')
      setup()

      expect(screen.getByText(label('Site management'))).toBeInTheDocument()
      expect(screen.queryByText(label('User management'))).not.toBeInTheDocument()
    })

    test('switching the filter writes it to the URL', async () => {
      const user = setup()
      await filterBy(user, 'Modified only')
      await vi.advanceTimersByTimeAsync(200)
      expect(window.location.search).toBe('?filter=modified')

      await filterBy(user, 'All settings')
      await vi.advanceTimersByTimeAsync(200)
      expect(window.location.search).toBe('')
    })

    test('the modified tag filters the page down to the modified settings', async () => {
      const user = setup({ ...searchData, topics: [mixedTopic, secondTopic] })

      await user.click(within(topic('User management')).getByRole('button', { name: '1 modified' }))

      expect(screen.getByRole('button', { name: 'Toggle Modified only' })).toHaveAttribute(
        'aria-pressed',
        'true'
      )
      expect(screen.getByText(label('Login session idle timeout'))).toBeInTheDocument()
      expect(
        screen.queryByText(label('Lock user accounts after N login failures'))
      ).not.toBeInTheDocument()
    })

    test('a tag collapses every topic but its own', async () => {
      const user = setup({ ...searchData, topics: [mixedTopic, secondTopic] })
      await user.click(screen.getByRole('button', { name: 'Expand all' }))
      expect(screen.getByText(label('Site setting'))).toBeInTheDocument()

      await user.click(within(topic('User management')).getByRole('button', { name: '1 modified' }))

      expect(screen.getByText(label('Login session idle timeout'))).toBeInTheDocument()
      expect(screen.queryByText(label('Site setting'))).not.toBeInTheDocument()
    })

    test('the site override tag filters the page down to the overridden settings', async () => {
      const user = setup({ ...searchData, topics: [overriddenTopic, secondTopic] })

      await user.click(screen.getByRole('button', { name: '1 overridden on sites' }))

      expect(
        screen.getByText(label('Lock user accounts after N login failures'))
      ).toBeInTheDocument()
      expect(screen.queryByText(label('Site management'))).not.toBeInTheDocument()
    })

    test('the empty state resets the search and the filter together', async () => {
      const user = setup()
      await search(user, 'idle')
      await filterBy(user, 'Modified only')

      await user.click(screen.getByRole('button', { name: 'Reset search' }))
      await vi.advanceTimersByTimeAsync(200)

      expect(screen.getByRole('searchbox')).toHaveValue('')
      expect(screen.getByRole('button', { name: 'Toggle All settings' })).toHaveAttribute(
        'aria-pressed',
        'true'
      )
    })
  })

  test('a search query in the URL pre-filters on mount', () => {
    window.history.replaceState({}, '', '/?search=Site+setting')
    setup()

    expect(screen.getByText(label('Site setting'))).toBeInTheDocument()
    expect(screen.queryByText(label('User management'))).not.toBeInTheDocument()
  })
})
