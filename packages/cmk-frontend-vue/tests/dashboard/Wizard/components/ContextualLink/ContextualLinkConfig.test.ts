/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import {
  type FilterDefinition,
  type FilterDefinitions,
  type FilterGroups,
  useProvideFilterDefinitions
} from 'cmk-ui-library/components/filter'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

import ContextualLinkConfig from '@/dashboard/components/Wizard/components/ContextualLink/ContextualLinkConfig.vue'
import type { ContextualLinkOptions } from '@/dashboard/components/Wizard/components/ContextualLink/contextualLink'
import { useContextualLink } from '@/dashboard/components/Wizard/components/ContextualLink/useContextualLink'
import type { HostStateContent, HostStatisticsContent } from '@/dashboard/components/Wizard/types'

import {
  dashboardMetadata,
  dashboardMetadataListHandler,
  viewsHandler
} from '@tests/dashboard/apiHandlers'

const HOST_STATISTICS_OPTIONS: ContextualLinkOptions = {
  modes: ['default', 'inherited', 'custom'],
  filters: ['sites', 'wato_folders', 'hostgroups', 'hoststate', 'host_labels'],
  filter_keys: {}
}

const server = useMswServer(
  // The target picker of the inherited and the custom mode lists the dashboards and the views.
  dashboardMetadataListHandler([dashboardMetadata('main', 'Overview', null)], { allOwners: false }),
  viewsHandler([])
)

afterEach(() => server.events.removeAllListeners())

function recordTargetRequests(): string[] {
  const requests: string[] = []
  server.events.on('request:start', ({ request }) => {
    requests.push(new URL(request.url).pathname.replace(/^.*\/domain-types\//, ''))
  })
  return requests
}

function renderConfig(
  options: ContextualLinkOptions = HOST_STATISTICS_OPTIONS,
  props: { defaultTarget?: TranslatedString; unavailable?: TranslatedString } = {},
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
  it('offers None and exactly the modes of the widget', () => {
    renderConfig({ ...HOST_STATISTICS_OPTIONS, modes: ['default'] })

    expect(
      screen.getAllByRole('button', { name: /^Toggle / }).map((button) => button.textContent)
    ).toEqual(['None', 'Default'])
  })

  it('starts a new link on the default target', () => {
    renderConfig()

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

    expect(screen.getByRole('button', { name: 'Toggle None' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
  })

  it('offers only None, saying why, when the widget cannot link', () => {
    renderConfig(
      HOST_STATISTICS_OPTIONS,
      { unavailable: untranslated('No line has a single service.') },
      {
        type: 'inherited',
        location: { type: 'dashboards', name: 'main' },
        include_context: true,
        include_time_range: false,
        show_filter_form: false
      }
    )

    expect(
      screen.getAllByRole('button', { name: /^Toggle / }).map((button) => button.textContent)
    ).toEqual(['None'])
    expect(screen.getByText('No line has a single service.')).toBeInTheDocument()
    expect(screen.queryByText('Target page')).not.toBeInTheDocument()
  })

  it('keeps the stored link when None is clicked on a widget that cannot link', async () => {
    const handler = renderConfig(
      HOST_STATISTICS_OPTIONS,
      { unavailable: untranslated('No line has a single service.') },
      {
        type: 'inherited',
        location: { type: 'dashboards', name: 'main' },
        include_context: true,
        include_time_range: false,
        show_filter_form: false
      }
    )

    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle None' }))

    expect(handler.enabled.value).toBe(true)
  })

  it('switches the link off from None', async () => {
    const handler = renderConfig()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle None' }))

    expect(handler.enabled.value).toBe(false)
  })

  it('describes the picked mode under its toggle', async () => {
    renderConfig()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle Inherited' }))

    expect(screen.getByText('Opens one view or dashboard.')).toBeInTheDocument()
    expect(screen.getByText('Always filtered by the clicked item.')).toBeInTheDocument()
  })

  it('names the built-in target in default mode', () => {
    renderConfig(HOST_STATISTICS_OPTIONS, { defaultTarget: untranslated('All hosts') })

    expect(screen.getByText('Target page')).toBeInTheDocument()
    expect(screen.getByText('All hosts')).toBeInTheDocument()
  })

  it('names no target page for a widget without a single built-in target', () => {
    renderConfig()

    expect(
      screen.getByText("Opens Checkmk's default page for the clicked item.")
    ).toBeInTheDocument()
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

  it('names the filters of the clicked item as always passed on', async () => {
    renderConfig()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle Inherited' }))

    expect(screen.getByText('(always passed on)')).toBeInTheDocument()
  })

  it('includes the dashboard and widget filters of a new inherited link', async () => {
    renderConfig()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle Inherited' }))

    expect(screen.getByRole('checkbox', { name: 'Dashboard & widget filters' })).toBeChecked()
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

    expect(screen.getByRole('checkbox', { name: 'Dashboard & widget filters' })).not.toBeChecked()
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
      .click(screen.getByRole('checkbox', { name: 'Filters from the clicked item' }))

    expect(screen.queryByRole('combobox', { name: 'Label key' })).not.toBeInTheDocument()
  })

  it('inserts a duplicate right after its link', async () => {
    const handler = renderCustomConfig()
    handler.addCustomLink()
    handler.customLinks.value[0]!.description = 'First'
    handler.customLinks.value[1]!.description = 'Second'

    await userEvent
      .setup()
      .click((await screen.findAllByRole('button', { name: 'Duplicate link' }))[0]!)

    expect(handler.customLinks.value.map(({ description }) => description)).toEqual([
      'First',
      'First',
      'Second'
    ])
  })

  it('names the target of a collapsed link next to its heading', async () => {
    const handler = renderCustomConfig()
    handler.customLinks.value[0]!.target = { type: 'dashboards', name: 'main' }

    await userEvent.setup().click(screen.getByRole('button', { name: /^Link 1/ }))

    expect(await screen.findByText('· Overview')).toBeInTheDocument()
  })

  it('says a collapsed link has no target yet', async () => {
    renderCustomConfig()

    await userEvent.setup().click(screen.getByRole('button', { name: /^Link 1/ }))

    expect(screen.getByText('· No target page yet')).toBeInTheDocument()
  })

  it('keeps the only link from being deleted', () => {
    renderCustomConfig()

    expect(screen.getByRole('button', { name: 'At least one link is needed' })).toBeDisabled()
  })

  it('deletes a link at once', async () => {
    const handler = renderCustomConfig()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Add another link' }))

    await user.click(screen.getAllByRole('button', { name: 'Delete link' })[0]!)

    expect(handler.customLinks.value).toHaveLength(1)
  })

  it('fetches no link targets until a mode with a target page is picked', async () => {
    const requests = recordTargetRequests()
    renderConfig()
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: 'Toggle None' }))
    expect(requests).toEqual([])
    await user.click(screen.getByRole('button', { name: 'Toggle Inherited' }))

    await waitFor(() => expect(requests).toHaveLength(2))
  })

  it('fetches the link targets once for all target pages', async () => {
    const requests = recordTargetRequests()
    const handler = renderCustomConfig()
    handler.addCustomLink()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Toggle Inherited' }))
    await user.click(screen.getByRole('button', { name: 'Toggle Custom' }))

    await user.click((await screen.findAllByRole('button', { name: /^Target page/ }))[1]!)
    await screen.findByRole('menuitem', { name: /^Overview/ })

    expect(requests.sort()).toEqual(['dashboard_metadata/collections/all', 'view/collections/all'])
  })
})
