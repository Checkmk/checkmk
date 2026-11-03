/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, within } from '@testing-library/vue'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

import ContextualLinkConfig from '@/dashboard/components/Wizard/components/ContextualLink/ContextualLinkConfig.vue'
import type { ContextualLinkOptions } from '@/dashboard/components/Wizard/components/ContextualLink/contextualLink'
import { useContextualLink } from '@/dashboard/components/Wizard/components/ContextualLink/useContextualLink'
import type { HostStateContent, HostStatisticsContent } from '@/dashboard/components/Wizard/types'

const API = `${location.protocol}//${location.host}/api/internal`
const HOST_STATISTICS_OPTIONS: ContextualLinkOptions = {
  modes: ['default', 'inherited', 'custom'],
  filters: ['siteopt', 'wato_folder', 'hoststate', 'opthostgroup'],
  filter_keys: {},
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
  props: { defaultTarget?: TranslatedString } = {},
  stored?: HostStatisticsContent['contextual_link']
) {
  const handler = useContextualLink<HostStatisticsContent>(options, stored)
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

const HOST_STATE_OPTIONS: ContextualLinkOptions = {
  modes: ['default', 'inherited', 'custom'],
  filters: ['host', 'host_labels'],
  filter_keys: { host_labels: { type: 'label', object_type: 'host' } },
  single_infos: ['host']
}

function renderCustomConfig() {
  const handler = useContextualLink<HostStateContent>(HOST_STATE_OPTIONS, undefined)
  handler.mode.value = 'custom'
  render(
    defineComponent({
      setup() {
        useProvideFilterDefinitions({ definitions: {}, groups: {} })
        return () => h(ContextualLinkConfig, { handler })
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

  it('names the target page of an inherited link', async () => {
    renderConfig()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle Inherited' }))

    expect(screen.getByText('Target page')).toBeInTheDocument()
  })

  it('lists what an inherited link always carries', async () => {
    renderConfig()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle Inherited' }))

    const included = within(screen.getByRole('list')).getAllByRole('listitem')
    expect(included.map((item) => item.textContent?.trim())).toEqual([
      'Applied dashboard & widget filters',
      'Contextual filter = clicked element'
    ])
  })

  it('lists only the clicked element for an inherited link without the filters', () => {
    renderConfig(
      HOST_STATISTICS_OPTIONS,
      {},
      {
        type: 'inherited',
        location: { type: 'views', name: 'allhosts', owner: null },
        include_context: false,
        include_time_range: false,
        show_filter_form: false
      }
    )

    const included = within(screen.getByRole('list')).getAllByRole('listitem')
    expect(included.map((item) => item.textContent?.trim())).toEqual([
      'Contextual filter = clicked element'
    ])
  })

  it('asks for a key for a label filter only', async () => {
    const handler = renderCustomConfig()
    const link = handler.customLinks.value[0]!

    handler.addFilter(link, 'host')
    handler.addFilter(link, 'host_labels')

    expect(await screen.findAllByRole('combobox', { name: 'Label key' })).toHaveLength(1)
  })

  it('hides the filters once the clicked element is unchecked', async () => {
    const handler = renderCustomConfig()
    handler.addFilter(handler.customLinks.value[0]!, 'host_labels')
    await screen.findByRole('combobox', { name: 'Label key' })

    await userEvent
      .setup()
      .click(screen.getByRole('checkbox', { name: 'Include filter context of clicked element' }))

    expect(screen.queryByRole('combobox', { name: 'Label key' })).not.toBeInTheDocument()
  })

  it('keeps a link when the deletion is cancelled', async () => {
    const handler = renderCustomConfig()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Add contextual link' }))

    await user.click(screen.getAllByRole('button', { name: 'Delete contextual link' })[0]!)
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(handler.customLinks.value).toHaveLength(2)
  })

  it('deletes a link once the deletion is confirmed', async () => {
    const handler = renderCustomConfig()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Add contextual link' }))

    await user.click(screen.getAllByRole('button', { name: 'Delete contextual link' })[0]!)
    await user.click(screen.getByRole('button', { name: 'Delete' }))

    expect(handler.customLinks.value).toHaveLength(1)
  })
})
