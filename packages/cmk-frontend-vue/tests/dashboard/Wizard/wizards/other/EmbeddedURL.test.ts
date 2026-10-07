/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import EmbeddedURL from '@/dashboard/components/Wizard/wizards/other/stage1/EmbeddedURL/EmbeddedURL.vue'
import type { GetValidWidgetProps } from '@/dashboard/components/Wizard/wizards/other/types'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { useProvideMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'

const API = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions`

const CONSTANTS: DashboardConstants = {
  responsive_grid_breakpoints: {},
  widgets: {
    url: {
      filter_context: { restricted_to_single: [] },
      layout: {
        relative: {
          initial_position: { x: 1, y: 1 },
          initial_size: { width: 30, height: 10 },
          is_resizable: true,
          minimum_size: { width: 1, height: 1 }
        },
        responsive: {}
      },
      title_macros: []
    }
  }
}

useMswServer(
  http.post(`${API}/compute-widget-titles/invoke`, () =>
    HttpResponse.json({ extensions: { titles: { preview_widget: 'Custom URL' } } })
  )
)

function openEmbeddedURL(editWidgetSpec: WidgetSpec | null) {
  const wizard = ref<GetValidWidgetProps>()
  const { range } = makeContentProps(null)
  render(
    defineComponent({
      setup() {
        useProvideDashboardConstants(CONSTANTS)
        useProvideMissingRuntimeFiltersAction(ref(true), () => {})
        return () =>
          h(EmbeddedURL, {
            ref: wizard,
            tick: 0,
            range,
            dashboardKey: { name: 'main', owner: 'cmkadmin' },
            editWidgetSpec
          })
      }
    })
  )
  return wizard
}

describe('EmbeddedURL', () => {
  it('leaves the dashboard filters out by default', () => {
    openEmbeddedURL(null)

    expect(screen.getByRole('checkbox', { name: 'Dashboard filters' })).not.toBeChecked()
  })

  it('requires a URL', async () => {
    const wizard = openEmbeddedURL(null)

    expect(wizard.value!.getValidWidgetProps()).toBeNull()
    expect(await screen.findByText('Value must be a valid URL')).toBeInTheDocument()
  })

  it('rejects a URL without an http or https scheme', async () => {
    const wizard = openEmbeddedURL(null)

    await fireEvent.update(
      screen.getByRole('textbox', { name: 'Enter URL to embed' }),
      'javascript:alert(1)'
    )

    expect(wizard.value!.getValidWidgetProps()).toBeNull()
    expect(await screen.findByText('Value must be a valid URL')).toBeInTheDocument()
  })

  it('includes the dashboard filters once checked', async () => {
    const wizard = openEmbeddedURL(null)

    await fireEvent.update(
      screen.getByRole('textbox', { name: 'Enter URL to embed' }),
      'https://example.com'
    )
    await fireEvent.click(screen.getByRole('checkbox', { name: 'Dashboard filters' }))

    await waitFor(() =>
      expect(wizard.value!.getValidWidgetProps()?.content).toMatchObject({
        include_context: true
      })
    )
  })

  it('keeps the stored choice of an edited widget', () => {
    openEmbeddedURL({
      content: { type: 'url', url: 'https://example.com', include_context: true },
      filter_context: { filters: {}, uses_infos: [] },
      general_settings: {
        title: { text: 'Custom URL', render_mode: 'with_background' },
        render_background: true
      }
    })

    expect(screen.getByRole('checkbox', { name: 'Dashboard filters' })).toBeChecked()
  })
})
