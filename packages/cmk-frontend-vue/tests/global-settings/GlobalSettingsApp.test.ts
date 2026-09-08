/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import type {
  GlobalSettingsApp as GlobalSettingsAppData,
  GlobalSettingsTopic
} from 'cmk-shared-typing/typescript/global_settings'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, test, vi } from 'vitest'

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

const data: GlobalSettingsAppData = {
  title: 'Global settings',
  domain: 'global_settings',
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
          modified: false,
          site_overrides: []
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
      modified: false,
      site_overrides: []
    }
  ]
}

const resettableTopic: GlobalSettingsTopic = {
  icon: 'users',
  headline: 'Resettable settings',
  subline: 'Everything in here was modified',
  warning: null,
  variables: [
    { ...data.topics[0]!.variables[0]!, modified: true },
    { ...booleanTopic.variables[0]!, value: true, modified: true }
  ]
}

interface Recorded {
  method: string
  ifMatch: string | null
  body: unknown
}
let requests: Recorded[] = []
let serverValue: { value: number; is_default: boolean } = { value: 15, is_default: false }
let booleanServerValue: { value: boolean; is_default: boolean } = { value: false, is_default: true }

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
    serverValue = { value: body.value, is_default: false }
    return HttpResponse.json(
      { varname: 'lock_on_logon_failures', ...serverValue },
      { headers: { ETag: '"v2"' } }
    )
  }),
  http.delete(SETTING_URL, ({ request }) => {
    requests.push({ method: 'DELETE', ifMatch: request.headers.get('If-Match'), body: null })
    serverValue = { value: 10, is_default: true }
    return new HttpResponse(null, { status: 204 })
  }),
  http.get(BOOLEAN_SETTING_URL, () => {
    requests.push({ method: 'GET', ifMatch: null, body: null })
    return HttpResponse.json(
      { varname: 'site_piggyback_hub', ...booleanServerValue },
      { headers: { ETag: '"b1"' } }
    )
  }),
  http.put(BOOLEAN_SETTING_URL, async ({ request }) => {
    const body = (await request.json()) as { value: boolean }
    requests.push({ method: 'PUT', ifMatch: request.headers.get('If-Match'), body })
    booleanServerValue = { value: body.value, is_default: false }
    return HttpResponse.json(
      { varname: 'site_piggyback_hub', ...booleanServerValue },
      { headers: { ETag: '"b2"' } }
    )
  }),
  http.delete(BOOLEAN_SETTING_URL, ({ request }) => {
    requests.push({ method: 'DELETE', ifMatch: request.headers.get('If-Match'), body: null })
    booleanServerValue = { value: false, is_default: true }
    return new HttpResponse(null, { status: 204 })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  requests = []
  serverValue = { value: 15, is_default: false }
  booleanServerValue = { value: false, is_default: true }
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

function settingRow() {
  return screen
    .getByRole('button', { name: 'Edit Lock user accounts after N login failures' })
    .closest('.global-settings-variable-row')
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
      modified: true
    }
  ]
}

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

  test('the topic header shows singular variable count and the number of modified variables', () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [...data.topics, secondTopic] } })
    expect(screen.getAllByText('1 variable')).toHaveLength(2)
    expect(screen.getByText('0 modified')).toBeInTheDocument()
    expect(screen.getByText('1 modified')).toBeInTheDocument()
  })

  test('the topic reset button is disabled while nothing is modified', () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [...data.topics, secondTopic] } })
    const [untouched, modified] = screen.getAllByRole('button', { name: 'Reset' })
    expect(untouched).toBeDisabled()
    expect(modified).toBeEnabled()
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
    const overriddenTopic: GlobalSettingsTopic = {
      ...data.topics[0]!,
      variables: [
        {
          ...data.topics[0]!.variables[0]!,
          site_overrides: [
            {
              site_id: 'remote_1',
              title: 'Remote site 1',
              url: '/remote_1/check_mk/wato.py?mode=edit_site_globals&site=remote_1'
            }
          ]
        }
      ]
    }
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

    await userEvent.click(within(dialog).getByRole('button', { name: 'Toggle Site overrides' }))
    expect(within(dialog).getByText('Remote site 1')).toBeVisible()
    expect(within(dialog).getByRole('link', { name: 'Open site settings' })).toHaveAttribute(
      'href',
      '/remote_1/check_mk/wato.py?mode=edit_site_globals&site=remote_1'
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
    serverValue = { value: 10, is_default: false }
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

  test('resetting a topic deletes every modified value guarded by its etag', async () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [resettableTopic] } })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item Resettable settings' })
    )
    expect(screen.getAllByText('(modified)')).toHaveLength(2)

    await userEvent.click(screen.getByRole('button', { name: 'Reset' }))
    const confirmation = screen.getByRole('alert')
    expect(confirmation).toHaveTextContent('Remove all modifications in "Resettable settings"?')
    await userEvent.click(within(confirmation).getByRole('button', { name: 'Remove' }))

    await waitFor(() =>
      expect(requests.map((r) => r.method)).toEqual([
        'GET',
        'DELETE',
        'GET',
        'GET',
        'DELETE',
        'GET'
      ])
    )
    expect(requests[1]!.ifMatch).toBe('"v1"')
    expect(requests[4]!.ifMatch).toBe('"b1"')
    await waitFor(() => expect(screen.queryByText('(modified)')).not.toBeInTheDocument())
    expect(screen.getByRole('switch', { name: 'Toggle Enable piggyback-hub' })).toHaveAttribute(
      'aria-checked',
      'false'
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  test('a rejected topic reset reports the server message and keeps the remaining values', async () => {
    server.use(
      http.delete(SETTING_URL, ({ request }) => {
        requests.push({ method: 'DELETE', ifMatch: request.headers.get('If-Match'), body: null })
        return HttpResponse.json(
          { title: 'Precondition failed', detail: 'ETag mismatch' },
          { status: 412 }
        )
      })
    )
    render(GlobalSettingsApp, { props: { ...data, topics: [resettableTopic] } })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item Resettable settings' })
    )
    expect(screen.getAllByText('(modified)')).toHaveLength(2)

    await userEvent.click(screen.getByRole('button', { name: 'Reset' }))
    await userEvent.click(within(screen.getByRole('alert')).getByRole('button', { name: 'Remove' }))

    expect(await screen.findByText(/ETag mismatch/)).toBeInTheDocument()
    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET', 'DELETE']))
    expect(screen.getAllByText('(modified)')).toHaveLength(2)
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
    const siteSettingUrl = `${location.protocol}//${location.host}/api/internal/objects/site_connection/remote_1/global_setting/lock_on_logon_failures`
    server.use(
      http.get(siteSettingUrl, () => {
        requests.push({ method: 'GET', ifMatch: null, body: null })
        return HttpResponse.json(
          { varname: 'lock_on_logon_failures', value: 15, is_default: false },
          { headers: { ETag: '"s1"' } }
        )
      }),
      http.put(siteSettingUrl, async ({ request }) => {
        requests.push({
          method: 'PUT',
          ifMatch: request.headers.get('If-Match'),
          body: await request.json()
        })
        return HttpResponse.json(
          { varname: 'lock_on_logon_failures', value: 20, is_default: false },
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

  test("resetting a topic on a site page removes only that site's explicit values", async () => {
    const siteUrl = (varname: string) =>
      `${location.protocol}//${location.host}/api/internal/objects/site_connection/remote_1/global_setting/${varname}`
    const siteRequests: Recorded[] = []
    let siteLock = { value: 10, is_default: false }
    let siteHub = { value: true, is_default: false }
    server.use(
      http.get(siteUrl('lock_on_logon_failures'), () => {
        siteRequests.push({ method: 'GET', ifMatch: null, body: null })
        return HttpResponse.json(
          { varname: 'lock_on_logon_failures', ...siteLock },
          { headers: { ETag: '"s1"' } }
        )
      }),
      http.delete(siteUrl('lock_on_logon_failures'), ({ request }) => {
        siteRequests.push({
          method: 'DELETE',
          ifMatch: request.headers.get('If-Match'),
          body: null
        })
        siteLock = { value: 10, is_default: true }
        return new HttpResponse(null, { status: 204 })
      }),
      http.get(siteUrl('site_piggyback_hub'), () => {
        siteRequests.push({ method: 'GET', ifMatch: null, body: null })
        return HttpResponse.json(
          { varname: 'site_piggyback_hub', ...siteHub },
          { headers: { ETag: '"sb1"' } }
        )
      }),
      http.delete(siteUrl('site_piggyback_hub'), ({ request }) => {
        siteRequests.push({
          method: 'DELETE',
          ifMatch: request.headers.get('If-Match'),
          body: null
        })
        siteHub = { value: false, is_default: true }
        return new HttpResponse(null, { status: 204 })
      })
    )
    render(GlobalSettingsApp, {
      props: { ...data, scope: { type: 'site', site_id: 'remote_1' }, topics: [resettableTopic] }
    })
    await userEvent.click(
      screen.getByRole('button', { name: 'Toggle accordion item Resettable settings' })
    )
    expect(screen.getAllByText('(modified)')).toHaveLength(2)

    await userEvent.click(screen.getByRole('button', { name: 'Reset' }))
    await userEvent.click(within(screen.getByRole('alert')).getByRole('button', { name: 'Remove' }))

    await waitFor(() =>
      expect(siteRequests.map((r) => r.method)).toEqual([
        'GET',
        'DELETE',
        'GET',
        'GET',
        'DELETE',
        'GET'
      ])
    )
    expect(siteRequests[1]!.ifMatch).toBe('"s1"')
    expect(siteRequests[4]!.ifMatch).toBe('"sb1"')
    expect(requests).toEqual([])
    await waitFor(() => expect(screen.queryByText('(modified)')).not.toBeInTheDocument())
    expect(screen.getByText('0 modified')).toBeInTheDocument()
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
          { varname: 'lock_on_logon_failures', value: 99, is_default: false },
          { headers: { ETag: '"stale"' } }
        )
      }),
      http.get(secondSettingUrl, () =>
        HttpResponse.json(
          { varname: 'site_setting', value: 42, is_default: false },
          { headers: { ETag: '"fresh"' } }
        )
      ),
      http.put(secondSettingUrl, ({ request }) => {
        putIfMatch = request.headers.get('If-Match')
        return HttpResponse.json(
          { varname: 'site_setting', value: 43, is_default: false },
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
