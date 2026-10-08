/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

import ContextualLinkConfig from '@/dashboard/components/Wizard/components/ContextualLink/ContextualLinkConfig.vue'
import type { ContextualLinkOptions } from '@/dashboard/components/Wizard/components/ContextualLink/contextualLink'
import { useContextualLink } from '@/dashboard/components/Wizard/components/ContextualLink/useContextualLink'
import type { HostStatisticsContent } from '@/dashboard/components/Wizard/types'

const API = `${location.protocol}//${location.host}/api/internal`
const HOST_STATISTICS_OPTIONS: ContextualLinkOptions = {
  modes: ['default', 'inherited', 'custom'],
  filters: ['siteopt', 'wato_folder', 'hoststate', 'opthostgroup'],
  single_infos: []
}

useMswServer(
  // The target picker of the inherited mode lists the views.
  http.get(`${API}/domain-types/view/collections/all`, () =>
    HttpResponse.json({ domainType: 'view', id: 'all', links: [], value: [] })
  ),
  http.get(`${API}/objects/constant/data_source/collections/all`, () =>
    HttpResponse.json({ domainType: 'constant', id: 'data_source', links: [], value: [] })
  )
)

function renderConfig(
  options: ContextualLinkOptions = HOST_STATISTICS_OPTIONS,
  props: { defaultTarget?: TranslatedString } = {}
) {
  const handler = useContextualLink<HostStatisticsContent>(options, undefined)
  render(
    defineComponent({
      setup() {
        useProvideFilterDefinitions({ definitions: {}, groups: {} })
        return () => h(ContextualLinkConfig, { handler, ...props })
      }
    })
  )
  return handler
}

describe('ContextualLinkConfig', () => {
  it('offers exactly the modes of the widget', () => {
    renderConfig({ ...HOST_STATISTICS_OPTIONS, modes: ['default'] })

    expect(screen.getByRole('button', { name: 'Toggle Default' })).toBeInTheDocument()
    expect(screen.queryAllByRole('button', { name: /^Toggle / })).toHaveLength(1)
  })

  it('names the built-in target in default mode', () => {
    renderConfig(HOST_STATISTICS_OPTIONS, { defaultTarget: untranslated('All hosts') })

    expect(screen.getByText('Target page')).toBeInTheDocument()
    expect(screen.getByText('All hosts')).toBeInTheDocument()
  })

  it('names no target page for a widget without a single built-in target', () => {
    renderConfig()

    expect(screen.getByText('Redirect to the default page defined by Checkmk.')).toBeInTheDocument()
    expect(screen.queryByText('Target page')).not.toBeInTheDocument()
  })

  it('switches the mode from its toggle', async () => {
    const handler = renderConfig()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle Inherited' }))

    expect(handler.mode.value).toBe('inherited')
  })
})
