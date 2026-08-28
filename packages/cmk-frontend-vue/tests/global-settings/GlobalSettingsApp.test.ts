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

interface Recorded {
  method: string
  ifMatch: string | null
  body: unknown
}
let requests: Recorded[] = []
let serverValue: { value: number; is_default: boolean } = { value: 15, is_default: false }

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
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  requests = []
  serverValue = { value: 15, is_default: false }
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

    await userEvent.click(screen.getByRole('button', { name: 'Toggle Expand all' }))
    expect(screen.getByText('Site setting')).toBeInTheDocument()
    expect(screen.getByText('Lock user accounts after N login failures')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Toggle Collapse all' }))
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
    await userEvent.click(screen.getByRole('button', { name: 'Toggle Expand all' }))
    expect(screen.getAllByText('(modified)')).toHaveLength(1)
    expect(
      screen.getByText('Site setting').closest('.global-settings-variable-row')
    ).toHaveTextContent('(modified)')
  })
})

describe('GlobalSettingsApp', () => {
  test('opening the editor loads the server value and refreshes the row', async () => {
    await openEditor()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('(modified)')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(15))
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

  test('resetting deletes the explicit value and shows the effective one afterwards', async () => {
    await openEditor()
    await userEvent.click(screen.getByRole('button', { name: /Remove modification/ }))
    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Remove' })
    )

    await waitFor(() => expect(requests.map((r) => r.method)).toEqual(['GET', 'DELETE', 'GET']))
    expect(requests[1]!.ifMatch).toBe('"v1"')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.queryByText('(modified)')).not.toBeInTheDocument()
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
    await userEvent.click(screen.getByRole('button', { name: 'Toggle Expand all' }))
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
