/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { reactive, ref } from 'vue'

import type { NewObjectDraft } from '@/maps/map/composables/useMapEditor'
import DraftFields from '@/maps/map/edit/components/DraftFields.vue'
import type { ObjectSuggestions } from '@/maps/map/edit/composables/useObjectSuggestions'

import { useMswServer } from '../../../support/http'
import { mapsGlobal } from '../../../support/services'

const API_BASE = `${location.protocol}//${location.host}/api/internal`
const HOSTS = ['heute', 'web01']

useMswServer(
  http.post(`${API_BASE}/objects/autocomplete/:ident`, async ({ params, request }) => {
    const { value } = (await request.json()) as { value: string }
    const choices =
      params.ident === 'monitored_hostname'
        ? HOSTS.filter((host) => host.includes(value)).map((host) => ({ id: host, value: host }))
        : []
    return HttpResponse.json({ choices })
  })
)

afterEach(() => cleanup())

function noSuggestions(): ObjectSuggestions {
  const empty = { items: ref([]), loading: ref(false) }
  return { aggregations: empty, maps: empty, aggregationFunctionOf: () => null }
}

function aServiceDraft(): NewObjectDraft {
  return reactive({
    type: 'service',
    host_name: 'heute',
    service_description: 'CPU load',
    group_name: '',
    map_name: '',
    aggregation_id: '',
    object_types: 'host',
    object_filter: '',
    expand_depth: 0,
    label_text: '',
    image_src: '',
    graph_url: ''
  })
}

describe('DraftFields', () => {
  it('drops the service when another host is picked', async () => {
    // The service was picked for the previous host; the new one may not run it.
    const draft = aServiceDraft()
    render(DraftFields, {
      props: { draft, suggestions: noSuggestions(), connectionId: 'local' },
      global: mapsGlobal()
    })

    await userEvent.click(screen.getByRole('combobox', { name: 'Host name' }))
    const filter = screen.getByRole('textbox', { name: 'filter' })
    await userEvent.clear(filter)
    await userEvent.type(filter, 'web')
    await userEvent.click(await screen.findByRole('option', { name: 'web01' }))

    await waitFor(() => expect(draft.host_name).toBe('web01'))
    expect(draft.service_description).toBe('')
  })
})
