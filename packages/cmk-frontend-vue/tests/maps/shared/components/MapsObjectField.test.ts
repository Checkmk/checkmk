/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { HttpResponse, http } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'

import MapsObjectField from '@/maps/shared/components/MapsObjectField.vue'
import type { MonitoringObjectKind } from '@/maps/shared/monitoringAutocompleters'

import { useMswServer } from '../../support/http'
import { mapsGlobal } from '../../support/services'

const API_BASE = `${location.protocol}//${location.host}/api/internal`

interface AutocompleteCall {
  ident: string
  value: string
  parameters: Record<string, unknown>
}

// Stands in for Checkmk's autocompleters: a site with more hosts than one page
// of answers holds, one host's services, and the configured groups.
const PAGE = 100
const HOSTS = [...Array.from({ length: 150 }, (_, i) => `srv-${i}`), 'heute']
const calls: AutocompleteCall[] = []

useMswServer(
  http.post(`${API_BASE}/objects/autocomplete/:ident`, async ({ params, request }) => {
    const body = (await request.json()) as Omit<AutocompleteCall, 'ident'>
    const ident = String(params.ident)
    calls.push({ ident, ...body })
    const choices: { id: string; value: string }[] = []
    if (ident === 'monitored_hostname') {
      choices.push(
        ...HOSTS.filter((host) => host.includes(body.value))
          .slice(0, PAGE)
          .map((host) => ({ id: host, value: host }))
      )
    } else if (ident === 'monitored_service_description') {
      choices.push({ id: 'CPU load', value: 'CPU load' })
    } else if (ident === 'allgroups') {
      choices.push({ id: 'linux', value: 'Linux servers' })
    }
    return HttpResponse.json({ choices })
  })
)

afterEach(() => {
  cleanup()
  calls.length = 0
})

function renderField(kind: MonitoringObjectKind, hostName?: string, modelValue = '') {
  return render(MapsObjectField, {
    props: {
      kind,
      hostName,
      modelValue,
      label: untranslated('Object'),
      placeholder: untranslated('Pick one')
    },
    global: mapsGlobal()
  })
}

async function open(): Promise<void> {
  await userEvent.click(screen.getByRole('combobox', { name: 'Object' }))
}

// The dropdown truncates its label into two spans, so the whole label is only
// readable as one string on the title the dropdown puts beside it.
function label(): string | null {
  const field = screen.getByRole('combobox', { name: 'Object' })
  return field.querySelector('[title]')?.getAttribute('title') ?? null
}

describe('MapsObjectField', () => {
  it('finds a host beyond the first page by searching on the server', async () => {
    renderField('host')
    await open()
    await userEvent.type(screen.getByRole('textbox', { name: 'filter' }), 'heu')

    expect(await screen.findByRole('option', { name: 'heute' })).toBeInTheDocument()
    expect(calls).toContainEqual(
      expect.objectContaining({ ident: 'monitored_hostname', value: 'heu' })
    )
  })

  it('keeps showing a stored host the site no longer knows', async () => {
    // The object is still bound to it: an empty field would hide that binding.
    renderField('host', undefined, 'decommissioned-01')

    await waitFor(() => expect(label()).toBe('decommissioned-01'))
  })

  it('offers the services of the picked host', async () => {
    renderField('service', 'web01')
    await open()

    expect(await screen.findByRole('option', { name: 'CPU load' })).toBeInTheDocument()
    expect(calls.at(-1)).toMatchObject({
      ident: 'monitored_service_description',
      parameters: { context: { host: { host: 'web01' } } }
    })
  })

  it('stays shut until a host is picked', async () => {
    renderField('service')
    await open()

    expect(screen.queryByRole('textbox', { name: 'filter' })).toBeNull()
    expect(calls).toEqual([])
  })

  it('looks a group up by its type and shows its alias', async () => {
    renderField('servicegroup')
    await open()

    expect(await screen.findByRole('option', { name: 'Linux servers' })).toBeInTheDocument()
    expect(calls.at(-1)).toMatchObject({
      ident: 'allgroups',
      parameters: { group_type: 'service' }
    })
  })
})
