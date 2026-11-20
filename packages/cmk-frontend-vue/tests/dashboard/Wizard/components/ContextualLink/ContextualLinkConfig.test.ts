/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import {
  type FilterDefinition,
  type FilterDefinitions,
  type FilterGroups,
  useProvideFilterDefinitions
} from 'cmk-ui-library/components/filter'
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
  filters: ['sites', 'wato_folders', 'hostgroups', 'hoststate', 'host_labels'],
  filter_keys: {}
}

useMswServer(
  // The target picker of the inherited and the custom mode lists the dashboards and the views.
  http.get(`${API}/domain-types/dashboard_metadata/collections/all`, () =>
    HttpResponse.json({
      domainType: 'dashboard_metadata',
      id: 'all',
      links: [],
      value: [
        {
          domainType: 'dashboard_metadata',
          id: 'main',
          links: [],
          extensions: {
            name: 'main',
            owner: null,
            is_built_in: true,
            is_editable: false,
            layout_type: 'relative_grid',
            display: { title: 'Overview' }
          }
        }
      ]
    })
  ),
  http.get(`${API}/domain-types/view/collections/all`, () =>
    HttpResponse.json({ domainType: 'view', id: 'all', links: [], value: [] })
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
  filter_keys: { host_labels: { type: 'label', object_type: 'host' } }
}

function filterDefinition(id: string, title: string, info: string, group: string | null) {
  return { id, title, extensions: { info, group } } as FilterDefinition
}

const FILTER_DEFINITIONS: FilterDefinitions = {
  host: filterDefinition('host', 'Host name', 'host', null),
  host_labels: filterDefinition('host_labels', 'Host labels', 'host', 'labels'),
  service_labels: filterDefinition('service_labels', 'Service labels', 'service', 'labels')
}
const FILTER_GROUPS = { labels: { title: 'Labels' } } as unknown as FilterGroups

function renderCustomConfig(
  options: ContextualLinkOptions = HOST_STATE_OPTIONS,
  definitions: FilterDefinitions = {}
) {
  const handler = useContextualLink<HostStateContent>(options, undefined)
  handler.mode.value = 'custom'
  render(
    defineComponent({
      setup() {
        useProvideFilterDefinitions({ definitions, groups: FILTER_GROUPS })
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

  it('starts a new link on the default target', () => {
    renderConfig()

    expect(screen.getByRole('checkbox', { name: 'Add contextual link' })).toBeChecked()
    expect(screen.getByRole('button', { name: 'Toggle Default' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
  })

  it('opens a stored inherited link on its mode and its target', async () => {
    renderConfig(
      HOST_STATISTICS_OPTIONS,
      {},
      {
        type: 'inherited',
        location: { type: 'dashboards', name: 'main' },
        include_context: true,
        include_time_range: false,
        show_filter_form: false
      }
    )

    expect(screen.getByRole('button', { name: 'Toggle Inherited' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
    const target = screen.getByRole('button', { name: /^Target page/ })
    await waitFor(() => expect(target).toHaveTextContent('Overview'))
  })

  it('opens a stored link that leads nowhere switched off', () => {
    renderConfig(HOST_STATISTICS_OPTIONS, {}, { type: 'none' })

    expect(screen.getByRole('checkbox', { name: 'Add contextual link' })).not.toBeChecked()
    expect(screen.queryAllByRole('button', { name: /^Toggle / })).toHaveLength(0)
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

  it('offers the target page of an inherited link', async () => {
    renderConfig()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle Inherited' }))

    expect(screen.getByRole('button', { name: 'Target page' })).toBeInTheDocument()
  })

  it('lists what an inherited link always carries', async () => {
    renderConfig()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle Inherited' }))

    const included = within(screen.getByRole('list')).getAllByRole('listitem')
    expect(included.map((item) => item.textContent?.trim())).toEqual([
      'Contextual filter = clicked element'
    ])
  })

  it('includes the dashboard and widget filters of a new inherited link', async () => {
    renderConfig()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle Inherited' }))

    expect(
      screen.getByRole('checkbox', { name: 'Include dashboard & widget filters' })
    ).toBeChecked()
  })

  it('opens a stored inherited link without the filters with them unchecked', () => {
    renderConfig(
      HOST_STATISTICS_OPTIONS,
      {},
      {
        type: 'inherited',
        location: { type: 'views', name: 'allhosts' },
        include_context: false,
        include_time_range: true,
        show_filter_form: false
      }
    )

    expect(
      screen.getByRole('checkbox', { name: 'Include dashboard & widget filters' })
    ).not.toBeChecked()
  })

  it('asks for a key for a label filter only', async () => {
    const handler = renderCustomConfig()
    const link = handler.customLinks.value[0]!

    handler.addFilter(link, 'host')
    handler.addFilter(link, 'host_labels')

    expect(await screen.findAllByRole('combobox', { name: 'Label key' })).toHaveLength(1)
  })

  it('offers the filters to add by the object they filter, each naming its group', async () => {
    renderCustomConfig(
      { ...HOST_STATE_OPTIONS, filters: ['host', 'host_labels', 'service_labels'] },
      FILTER_DEFINITIONS
    )

    await userEvent.setup().click(screen.getByRole('button', { name: 'Add filter' }))

    expect(
      screen.getAllByRole('button', { name: /^Toggle .*\(/ }).map((button) => button.textContent)
    ).toEqual(['All (3)', 'Host (2)', 'Service (1)'])
    expect(screen.getAllByRole('menuitem').map((item) => item.getAttribute('aria-label'))).toEqual([
      'Host name',
      'Host labels – Labels',
      'Service labels – Labels'
    ])
  })

  it('offers no toggle when all filters to add filter the same object', async () => {
    renderCustomConfig(HOST_STATE_OPTIONS, FILTER_DEFINITIONS)

    await userEvent.setup().click(screen.getByRole('button', { name: 'Add filter' }))

    expect(await screen.findAllByRole('menuitem')).toHaveLength(2)
    expect(screen.queryByRole('button', { name: /^Toggle .*\(/ })).not.toBeInTheDocument()
  })

  it('adds the filter picked from the filters to add', async () => {
    const handler = renderCustomConfig(HOST_STATE_OPTIONS, FILTER_DEFINITIONS)
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: 'Add filter' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Host labels – Labels' }))

    expect(handler.customLinks.value[0]!.filters.map(({ filterId }) => filterId)).toEqual([
      'host_labels'
    ])
  })

  it('offers a filter without a definition by its id', async () => {
    renderCustomConfig()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Add filter' }))

    expect(screen.getAllByRole('menuitem').map((item) => item.getAttribute('aria-label'))).toEqual([
      'host',
      'host_labels'
    ])
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
