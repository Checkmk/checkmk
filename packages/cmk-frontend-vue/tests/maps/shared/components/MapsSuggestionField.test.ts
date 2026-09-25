/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import type { Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'
import { type Ref, ref } from 'vue'

import MapsSuggestionField from '@/maps/shared/components/MapsSuggestionField.vue'
import { type SuggestionList, namedSuggestions } from '@/maps/shared/suggestions'

import { mapsGlobal } from '../../support/services'

/**
 * A list still on its way, whose entries a case fills in by hand. The refs are
 * writable — the point of every case here is what happens when the answer
 * lands — while the return type pins the fake to the real interface.
 */
function aLoadingList(): SuggestionList & {
  items: Ref<Suggestion[]>
  loading: Ref<boolean>
} {
  return { items: ref([]), loading: ref(true) }
}

function renderField(list: SuggestionList, modelValue: string) {
  return render(MapsSuggestionField, {
    props: {
      list,
      modelValue,
      label: untranslated('Hostname'),
      placeholder: untranslated('hostname'),
      emptyHint: untranslated('No hosts available')
    },
    global: mapsGlobal()
  })
}

// The dropdown truncates its label into two spans, so the whole label is only
// readable as one string on the title the dropdown puts beside it.
function label(): string | null {
  const field = screen.getByRole('combobox', { name: 'Hostname' })
  return field.querySelector('[title]')?.getAttribute('title') ?? null
}

describe('MapsSuggestionField', () => {
  it('shows the picked value once a list that was still loading arrives', async () => {
    // What the properties card does: it opens on an object that already names a
    // host, while the host list is still on its way.
    const list = aLoadingList()
    renderField(list, 'web01')
    await waitFor(() => expect(label()).toBe('Loading…'))

    list.items.value = namedSuggestions(['web01', 'web02'])
    list.loading.value = false

    await waitFor(() => expect(label()).toBe('web01'))
  })

  it('says the list is loading when opened before it arrives', async () => {
    const list = aLoadingList()
    renderField(list, '')
    await userEvent.click(screen.getByRole('combobox', { name: 'Hostname' }))

    expect(await screen.findByText('Loading…')).toBeInTheDocument()

    list.items.value = namedSuggestions(['web01'])
    list.loading.value = false

    expect(await screen.findByRole('option', { name: 'web01' })).toBeInTheDocument()
  })

  it('stops claiming to load when the list comes back empty', async () => {
    const list = aLoadingList()
    renderField(list, 'web01')
    await waitFor(() => expect(label()).toBe('Loading…'))

    // As the loaders do it: the answer is assigned, then the flag drops.
    list.items.value = namedSuggestions([])
    list.loading.value = false

    await waitFor(() => expect(label()).toBe('No hosts available'))
  })
})
