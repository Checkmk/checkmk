/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import * as cmkFetch from '@/lib/cmkFetch'

import ConfigureGeneralProperties, {
  _resetSiteCache
} from '@/mode-otel/otel-configuration-steps/ConfigureGeneralProperties.vue'

type RawSite = { id: string; title: string; extensions?: { logged_in?: boolean } }

// Sites where 'local' has no extensions field (local site = ApiOmitted logged_in)
const SITES: RawSite[] = [
  { id: 'remote1', title: 'Remote Site 1', extensions: { logged_in: false } },
  { id: 'local', title: 'Local Site' },
  { id: 'remote2', title: 'Remote Site 2', extensions: { logged_in: true } }
]

function mockSitesResponse(sites: RawSite[]) {
  return vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue({
    raiseForStatus: vi.fn().mockResolvedValue(undefined),
    json: vi.fn().mockResolvedValue({ value: sites })
  } as unknown as cmkFetch.CmkFetchResponse)
}

function mockSitesError() {
  vi.spyOn(cmkFetch, 'fetchRestAPI').mockRejectedValue(new Error('Network error'))
}

/**
 * Render ConfigureGeneralProperties inside a wrapper that captures the reactive
 * model state and exposes the component ref for calling validate().
 */
function renderComponent(initialConfigName = '', initialSiteId: string | null = null) {
  const configName = ref(initialConfigName)
  const siteId = ref(initialSiteId)
  const compRef = ref<InstanceType<typeof ConfigureGeneralProperties>>()

  render(
    defineComponent({
      components: { ConfigureGeneralProperties },
      setup: () => ({ configName, siteId, compRef }),
      template: `<ConfigureGeneralProperties ref="compRef" v-model:config-name="configName" v-model:site-id="siteId" />`
    })
  )

  return { configName, siteId, compRef }
}

describe('ConfigureGeneralProperties', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    _resetSiteCache()
  })

  describe('site pre-selection', () => {
    test('pre-selects the local site (no logged_in key in extensions)', async () => {
      mockSitesResponse(SITES)
      const { siteId } = renderComponent()

      await waitFor(() => expect(siteId.value).toBe('local'))
    })

    test('falls back to first site when no local site is identifiable', async () => {
      const allRemote: RawSite[] = [
        { id: 'remote1', title: 'Remote 1', extensions: { logged_in: false } },
        { id: 'remote2', title: 'Remote 2', extensions: { logged_in: true } }
      ]
      mockSitesResponse(allRemote)
      const { siteId } = renderComponent()

      await waitFor(() => expect(siteId.value).toBe('remote1'))
    })

    test('does not overwrite siteId when already set (navigating back)', async () => {
      const spy = mockSitesResponse(SITES)
      const { siteId } = renderComponent('', 'remote2')

      // Wait for the API call to complete
      await waitFor(() => expect(spy).toHaveBeenCalledTimes(1))
      // Allow the async body of onMounted to finish
      await new Promise((r) => setTimeout(r, 0))

      expect(siteId.value).toBe('remote2')
    })

    test('uses cached sites on re-mount without a second network call', async () => {
      const spy = mockSitesResponse(SITES)

      // First mount — populates cache
      const { siteId: siteId1 } = renderComponent()
      await waitFor(() => expect(siteId1.value).toBe('local'))
      cleanup()

      // Second mount — should use cache, not call fetchRestAPI again
      const { siteId: siteId2 } = renderComponent()
      await waitFor(() => expect(siteId2.value).toBe('local'))

      expect(spy).toHaveBeenCalledTimes(1)
    })
  })

  describe('error handling', () => {
    test('shows error message when site loading fails', async () => {
      mockSitesError()
      renderComponent()

      await screen.findByText('Failed to load sites. Please try again.')
    })
  })

  describe('loading state', () => {
    test('validate() returns false while sites are still loading', async () => {
      // Never-resolving promise keeps isLoading true
      vi.spyOn(cmkFetch, 'fetchRestAPI').mockReturnValue(new Promise(() => {}))

      const { compRef } = renderComponent('valid_name', null)
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      // No validation errors shown — loading is not a user error
      expect(
        screen.queryByText('Configuration name is required but not specified.')
      ).not.toBeInTheDocument()
    })
  })

  describe('validation', () => {
    test('does not show validation errors before validate() is called', async () => {
      mockSitesResponse([])
      renderComponent()

      expect(
        screen.queryByText('Configuration name is required but not specified.')
      ).not.toBeInTheDocument()
      expect(screen.queryByText('Site is required but not specified.')).not.toBeInTheDocument()
    })

    test('validate() returns false and shows errors for empty config name', async () => {
      mockSitesResponse([])
      const { compRef } = renderComponent('', null)

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Configuration name is required but not specified.')
    })

    test('validate() returns false and shows error for missing site', async () => {
      // Empty site list so siteId stays null after mount
      mockSitesResponse([])
      const { compRef } = renderComponent('valid_name', null)

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Site is required but not specified.')
    })

    test('validate() returns true when config name and site are both valid', async () => {
      mockSitesResponse(SITES)
      const { compRef, siteId } = renderComponent('valid_name', null)

      await waitFor(() => expect(siteId.value).toBe('local'))
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('validate() returns false for invalid config name pattern', async () => {
      mockSitesResponse(SITES)
      const { compRef, siteId } = renderComponent('123-invalid-start', null)

      await waitFor(() => expect(siteId.value).toBe('local'))
      await waitFor(() => expect(compRef.value).toBeDefined())

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText(
        'The name must only consist of letters, digits, dash and underscore and it must start with a letter or underscore.'
      )
    })
  })
})
