/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { Response } from 'cmk-ui-library/components/CmkSuggestions'
import { fetchSuggestions } from 'cmk-ui-library/components/FormAutocompleter/autocompleter'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { computed, nextTick, ref } from 'vue'

import { useLabelValueAutocomplete } from '@/dashboard/components/Wizard/components/autocompleters/useLabelValueAutocomplete'
import type { LabelValueItem } from '@/dashboard/components/Wizard/types'

vi.mock('cmk-ui-library/components/FormAutocompleter/autocompleter', () => ({
  fetchSuggestions: vi.fn()
}))

const autocompleter = computed<Autocompleter>(() => ({
  fetch_method: 'rest_autocomplete',
  data: { ident: 'monitored_metrics', params: {} }
}))

const deferred = () => {
  let resolve!: (response: Response) => void
  const promise = new Promise<Response>((r) => {
    resolve = r
  })
  return { promise, resolve }
}

const setUp = () => {
  const model = ref<LabelValueItem | null>(null)
  return { model, ...useLabelValueAutocomplete(model, autocompleter) }
}

describe('useLabelValueAutocomplete', () => {
  beforeEach(() => {
    vi.mocked(fetchSuggestions).mockReset()
  })

  it('commits the selected value before the suggestions are fetched', async () => {
    vi.mocked(fetchSuggestions).mockReturnValue(deferred().promise)
    const { model, internalValue } = setUp()

    internalValue.value = 'util'
    await nextTick()

    expect(model.value).toEqual({ value: 'util', label: 'util' })
  })

  it('refines the label once the suggestions resolve', async () => {
    const lookup = deferred()
    vi.mocked(fetchSuggestions).mockReturnValue(lookup.promise)
    const { model, internalValue } = setUp()

    internalValue.value = 'util'
    await nextTick()
    lookup.resolve(new Response([{ name: 'util', title: 'CPU utilization' }]))
    await lookup.promise

    expect(model.value).toEqual({ value: 'util', label: 'CPU utilization' })
  })

  it('ignores a response that a newer selection has superseded', async () => {
    const first = deferred()
    const second = deferred()
    vi.mocked(fetchSuggestions)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise)
    const { model, internalValue } = setUp()

    internalValue.value = 'util'
    await nextTick()
    internalValue.value = 'mem_used'
    await nextTick()

    second.resolve(new Response([{ name: 'mem_used', title: 'Memory used' }]))
    await second.promise
    first.resolve(new Response([{ name: 'util', title: 'CPU utilization' }]))
    await first.promise

    expect(model.value).toEqual({ value: 'mem_used', label: 'Memory used' })
  })

  it('keeps the model cleared when the value is reset while a fetch is in flight', async () => {
    const lookup = deferred()
    vi.mocked(fetchSuggestions).mockReturnValue(lookup.promise)
    const { model, internalValue } = setUp()

    internalValue.value = 'util'
    await nextTick()
    internalValue.value = null
    await nextTick()
    lookup.resolve(new Response([{ name: 'util', title: 'CPU utilization' }]))
    await lookup.promise

    expect(model.value).toBeNull()
  })

  it('ignores a response for a value that was left and selected again', async () => {
    const first = deferred()
    const second = deferred()
    vi.mocked(fetchSuggestions)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise)
    const { model, internalValue } = setUp()

    internalValue.value = 'util'
    await nextTick()
    internalValue.value = null
    await nextTick()
    internalValue.value = 'util'
    await nextTick()

    second.resolve(new Response([{ name: 'util', title: 'CPU utilization' }]))
    await second.promise
    first.resolve(new Response([{ name: 'util', title: 'Superseded lookup' }]))
    await first.promise

    expect(model.value).toEqual({ value: 'util', label: 'CPU utilization' })
  })

  it('stays pending when a lookup for an earlier selection of the same value returns', async () => {
    const first = deferred()
    const second = deferred()
    vi.mocked(fetchSuggestions)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise)
    const { internalValue, pending } = setUp()

    internalValue.value = 'util'
    await nextTick()
    internalValue.value = null
    await nextTick()
    internalValue.value = 'util'
    await nextTick()

    first.resolve(new Response([{ name: 'util', title: 'Superseded lookup' }]))
    await first.promise

    expect(pending.value).toBe(true)
  })

  it('reports pending until the fetch that owns the current value resolves', async () => {
    const first = deferred()
    const second = deferred()
    vi.mocked(fetchSuggestions)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise)
    const { internalValue, pending } = setUp()

    expect(pending.value).toBe(false)

    internalValue.value = 'util'
    await nextTick()
    internalValue.value = 'mem_used'
    await nextTick()
    expect(pending.value).toBe(true)

    first.resolve(new Response([{ name: 'util', title: 'CPU utilization' }]))
    await first.promise
    expect(pending.value).toBe(true)

    second.resolve(new Response([{ name: 'mem_used', title: 'Memory used' }]))
    await second.promise
    expect(pending.value).toBe(false)
  })
})
