/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, delay, http } from 'msw'
import { setupServer } from 'msw/node'
import { defineComponent, ref } from 'vue'

import ConfigureGeneralProperties, {
  _resetCaches,
  nextAvailableConfigName
} from '@/mode-otel/otel-configuration-steps/ConfigureGeneralProperties.vue'

const API_BASE = `${location.protocol}//${location.host}/api/internal`
const SITES_URL = `${API_BASE}/domain-types/site_connection/collections/all`
const RECEIVERS_URL = `${API_BASE}/domain-types/otel_collector_config_receivers/collections/all`
const PROM_SCRAPE_URL = `${API_BASE}/domain-types/otel_collector_config_prom_scrape/collections/all`

type RawSite = { id: string; title: string; extensions: { logged_in?: boolean } }

// The local site is the one whose extensions omit `logged_in`.
const SITES: RawSite[] = [
  { id: 'remote1', title: 'Remote Site 1', extensions: { logged_in: false } },
  { id: 'local', title: 'Local Site', extensions: {} },
  { id: 'remote2', title: 'Remote Site 2', extensions: { logged_in: true } }
]

const server = setupServer()

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterAll(() => server.close())

/** Counts the site-list requests that actually reached the backend. */
let siteRequests = 0

function serveSites(sites: RawSite[], existingConfigs: unknown[] = []) {
  server.use(
    http.get(SITES_URL, () => {
      siteRequests += 1
      return HttpResponse.json({ value: sites })
    }),
    http.get(RECEIVERS_URL, () => HttpResponse.json({ value: existingConfigs })),
    http.get(PROM_SCRAPE_URL, () => HttpResponse.json({ value: existingConfigs }))
  )
}

function serveSitesError() {
  // onMounted also loads the config list, so that endpoint still needs a handler.
  serveSites([])
  server.use(http.get(SITES_URL, () => HttpResponse.json({ title: 'Boom' }, { status: 500 })))
}

/**
 * Render ConfigureGeneralProperties inside a wrapper that captures the reactive
 * model state and exposes the component ref for calling validate().
 */
const OTEL_PROPS = {
  configNamePrefix: 'opentelemetry_config_',
  configKind: 'receivers',
  alreadyConfiguredError:
    'OpenTelemetry is already configured for this site. Select another site or update the existing configuration.'
}

const PROMETHEUS_PROPS = {
  configNamePrefix: 'prometheus_config_',
  configKind: 'prom_scrape',
  alreadyConfiguredError:
    'Prometheus is already configured for this site. Select another site or update the existing configuration.'
}

function renderComponent(
  initialConfigName = '',
  initialSiteId: string | null = null,
  propsOverride: typeof OTEL_PROPS = OTEL_PROPS
) {
  const configName = ref(initialConfigName)
  const siteId = ref(initialSiteId)
  const compRef = ref<InstanceType<typeof ConfigureGeneralProperties>>()

  render(
    defineComponent({
      components: { ConfigureGeneralProperties },
      setup: () => ({ configName, siteId, compRef, ...propsOverride }),
      template: `<ConfigureGeneralProperties ref="compRef" v-model:config-name="configName" v-model:site-id="siteId" :config-name-prefix="configNamePrefix" :config-kind="configKind" :already-configured-error="alreadyConfiguredError" />`
    })
  )

  return { configName, siteId, compRef }
}

describe('ConfigureGeneralProperties', () => {
  beforeEach(() => {
    siteRequests = 0
  })

  afterEach(() => {
    cleanup()
    server.resetHandlers()
    vi.restoreAllMocks()
    _resetCaches()
  })

  describe('site pre-selection', () => {
    test('pre-selects the local site (no logged_in key in extensions)', async () => {
      serveSites(SITES)
      const { siteId } = renderComponent()

      await waitFor(() => expect(siteId.value).toBe('local'))
    })

    test('falls back to first site when no local site is identifiable', async () => {
      const allRemote: RawSite[] = [
        { id: 'remote1', title: 'Remote 1', extensions: { logged_in: false } },
        { id: 'remote2', title: 'Remote 2', extensions: { logged_in: true } }
      ]
      serveSites(allRemote)
      const { siteId } = renderComponent()

      await waitFor(() => expect(siteId.value).toBe('remote1'))
    })

    test('does not overwrite siteId when already set (navigating back)', async () => {
      serveSites(SITES)
      const { siteId } = renderComponent('', 'remote2')

      await waitFor(() => expect(siteRequests).toBe(1))
      // Allow the async body of onMounted to finish
      await new Promise((r) => setTimeout(r, 0))

      expect(siteId.value).toBe('remote2')
    })

    test('uses cached sites on re-mount without a second network call', async () => {
      serveSites(SITES)

      // First mount — populates cache
      const { siteId: siteId1 } = renderComponent()
      await waitFor(() => expect(siteId1.value).toBe('local'))
      cleanup()

      // Second mount — should use cache, not fetch the site list again
      const { siteId: siteId2 } = renderComponent()
      await waitFor(() => expect(siteId2.value).toBe('local'))

      expect(siteRequests).toBe(1)
    })
  })

  describe('config name prefill', () => {
    test('prefills the first slot when no configuration exists yet', async () => {
      serveSites(SITES, [])
      const { configName } = renderComponent()

      await waitFor(() => expect(configName.value).toBe('opentelemetry_config_1'))
    })

    test('prefills the next slot after the highest existing index', async () => {
      const existingConfigs = [{ id: 'opentelemetry_config_1' }, { id: 'opentelemetry_config_2' }]
      serveSites(SITES, existingConfigs)
      const { configName } = renderComponent()

      await waitFor(() => expect(configName.value).toBe('opentelemetry_config_3'))
    })

    test('uses the prometheus prefix for the prometheus wizard', async () => {
      const existingConfigs = [{ id: 'prometheus_config_1' }]
      serveSites(SITES, existingConfigs)
      const { configName } = renderComponent('', null, PROMETHEUS_PROPS)

      await waitFor(() => expect(configName.value).toBe('prometheus_config_2'))
    })

    test('does not overwrite a name the user already entered', async () => {
      serveSites(SITES, [{ id: 'opentelemetry_config_1' }])
      const { configName } = renderComponent('my_custom_name')

      // Let the async onMounted body run.
      await new Promise((r) => setTimeout(r, 0))

      expect(configName.value).toBe('my_custom_name')
    })

    test('falls back to the first slot when the config list call fails', async () => {
      serveSites(SITES)
      server.use(
        http.get(RECEIVERS_URL, () => HttpResponse.json({ title: 'Boom' }, { status: 500 }))
      )
      const { configName } = renderComponent()

      await waitFor(() => expect(configName.value).toBe('opentelemetry_config_1'))
    })
  })

  describe('error handling', () => {
    test('shows error message when site loading fails', async () => {
      serveSitesError()
      renderComponent()

      await screen.findByText('Failed to load sites. Please try again.')
    })
  })

  describe('loading state', () => {
    test('validate() returns false while sites are still loading', async () => {
      // A request that never settles keeps isLoading true
      serveSites(SITES)
      server.use(http.get(SITES_URL, () => delay('infinite')))

      const { compRef } = renderComponent('valid_name', null)
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = await compRef.value!.validate()

      expect(result).toBe(false)
      // No validation errors shown — loading is not a user error
      expect(
        screen.queryByText('Configuration name is required but not specified.')
      ).not.toBeInTheDocument()
    })
  })

  describe('validation', () => {
    test('does not show validation errors before validate() is called', async () => {
      serveSites([])
      renderComponent()

      expect(
        screen.queryByText('Configuration name is required but not specified.')
      ).not.toBeInTheDocument()
      expect(screen.queryByText('Site is required but not specified.')).not.toBeInTheDocument()
    })

    test('validate() returns false and shows errors for empty config name', async () => {
      serveSites([])
      const { compRef, configName } = renderComponent('', null)

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))
      // The field is prefilled on mount, so clear it to exercise the
      // "name is required" validation a user would hit by emptying it.
      configName.value = ''

      const result = await compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Configuration name is required but not specified.')
    })

    test('validate() returns false and shows error for missing site', async () => {
      // Empty site list so siteId stays null after mount
      serveSites([])
      const { compRef } = renderComponent('valid_name', null)

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = await compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Site is required but not specified.')
    })

    test('validate() returns true when config name and site are both valid', async () => {
      serveSites(SITES)
      const { compRef, siteId } = renderComponent('valid_name', null)

      await waitFor(() => expect(siteId.value).toBe('local'))
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = await compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('validate() returns false for invalid config name pattern', async () => {
      serveSites(SITES)
      const { compRef, siteId } = renderComponent('123-invalid-start', null)

      await waitFor(() => expect(siteId.value).toBe('local'))
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = await compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText(
        'The name must only consist of letters, digits, dash and underscore and it must start with a letter or underscore.'
      )
    })

    test('validate() returns false when site already has OTel config', async () => {
      const existingConfigs = [{ extensions: { site: ['local'] } }]
      serveSites(SITES, existingConfigs)
      const { compRef, siteId } = renderComponent('valid_name', null)

      await waitFor(() => expect(siteId.value).toBe('local'))
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = await compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText(
        'OpenTelemetry is already configured for this site. Select another site or update the existing configuration.'
      )
    })

    test('validate() returns false when site already has Prometheus config', async () => {
      const existingConfigs = [{ extensions: { site: ['local'] } }]
      serveSites(SITES, existingConfigs)
      const { compRef, siteId } = renderComponent('valid_name', null, PROMETHEUS_PROPS)

      await waitFor(() => expect(siteId.value).toBe('local'))
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = await compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText(
        'Prometheus is already configured for this site. Select another site or update the existing configuration.'
      )
    })

    test('validate() passes when site has no existing config', async () => {
      serveSites(SITES)
      const { compRef, siteId } = renderComponent('valid_name', null)

      await waitFor(() => expect(siteId.value).toBe('local'))
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = await compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('validate() passes when config exists on a different site', async () => {
      const existingConfigs = [{ extensions: { site: ['other_site'] } }]
      serveSites(SITES, existingConfigs)
      const { compRef, siteId } = renderComponent('valid_name', null)

      await waitFor(() => expect(siteId.value).toBe('local'))
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = await compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('validate() returns false when site has a disabled config', async () => {
      const existingConfigs = [{ extensions: { site: ['local'], disabled: true } }]
      serveSites(SITES, existingConfigs)
      const { compRef, siteId } = renderComponent('valid_name', null)

      await waitFor(() => expect(siteId.value).toBe('local'))
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = await compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText(
        'OpenTelemetry is already configured for this site. Select another site or update the existing configuration.'
      )
    })

    test('validate() returns false when the config name is already taken on another site', async () => {
      const existingConfigs = [
        { id: 'opentelemetry_config_1', extensions: { site: ['other_site'] } }
      ]
      serveSites(SITES, existingConfigs)
      const { compRef, siteId } = renderComponent('opentelemetry_config_1', null)

      await waitFor(() => expect(siteId.value).toBe('local'))
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = await compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText(
        'A configuration with this name already exists. Choose a different name.'
      )
    })

    test('validate() sees a config added after mount (skips the prefill cache)', async () => {
      // Empty at mount, so prefill caches an empty list; a config for the
      // selected site appears before the user submits. Validation must catch
      // it instead of relying on the stale cache.
      let liveConfigs: unknown[] = []
      serveSites(SITES)
      server.use(http.get(RECEIVERS_URL, () => HttpResponse.json({ value: liveConfigs })))
      const { compRef, siteId } = renderComponent('valid_name', null)

      await waitFor(() => expect(siteId.value).toBe('local'))
      await waitFor(() => expect(compRef.value).toBeDefined())

      // Config added on the backend after the component mounted.
      liveConfigs = [{ extensions: { site: ['local'] } }]

      const result = await compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText(
        'OpenTelemetry is already configured for this site. Select another site or update the existing configuration.'
      )
    })

    test('validate() returns false when config check API fails', async () => {
      serveSites(SITES)
      server.use(
        http.get(RECEIVERS_URL, () => HttpResponse.json({ title: 'Boom' }, { status: 500 }))
      )
      const { compRef, siteId } = renderComponent('valid_name', null)

      await waitFor(() => expect(siteId.value).toBe('local'))
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = await compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Failed to validate site configuration. Please try again.')
    })
  })
})

describe('nextAvailableConfigName', () => {
  test('returns the first slot for an empty list', () => {
    expect(nextAvailableConfigName([], 'opentelemetry_config_')).toBe('opentelemetry_config_1')
  })

  test('returns max(existing) + 1', () => {
    expect(
      nextAvailableConfigName(
        ['opentelemetry_config_1', 'opentelemetry_config_2'],
        'opentelemetry_config_'
      )
    ).toBe('opentelemetry_config_3')
  })

  test('skips gaps by using the highest index, not the count', () => {
    expect(
      nextAvailableConfigName(
        ['opentelemetry_config_1', 'opentelemetry_config_5'],
        'opentelemetry_config_'
      )
    ).toBe('opentelemetry_config_6')
  })

  test('ignores ids that do not match the prefix or are not numbered', () => {
    expect(
      nextAvailableConfigName(
        [
          'my_custom_name',
          'opentelemetry_config_',
          'opentelemetry_config_2',
          'prometheus_config_9'
        ],
        'opentelemetry_config_'
      )
    ).toBe('opentelemetry_config_3')
  })
})
