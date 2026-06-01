/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'

import { Response } from '@/components/CmkSuggestions/suggestions'

import AttributeFilterPill from '@/metric-backend/attribute-filter/AttributeFilterPill.vue'
import FormAttributeFilter from '@/metric-backend/attribute-filter/FormAttributeFilter.vue'
import type { AttributeFilterModel, AttributeType } from '@/metric-backend/attribute-filter/types'

function makeModel(): AttributeFilterModel {
  return [
    {
      id: 'pill-a',
      attributeType: null,
      key: '',
      operator: 'eq',
      value: '',
      connector: 'AND'
    },
    {
      id: 'pill-b',
      attributeType: 'scope',
      key: 'otel.library.name',
      operator: 'eq',
      value: '',
      connector: 'AND'
    }
  ]
}

function noopQuerySuggestions(_: string): Promise<Response> {
  return Promise.resolve(new Response([]))
}

function mountForm(
  initial: AttributeFilterModel,
  resolve?: (key: string) => AttributeType,
  { attach = false }: { attach?: boolean } = {}
) {
  const model = ref<AttributeFilterModel>(initial)
  const wrapperComponent = defineComponent({
    components: { FormAttributeFilter },
    setup() {
      return { model, querySuggestions: noopQuerySuggestions, resolveAttributeType: resolve }
    },
    template: `
      <FormAttributeFilter
        v-model="model"
        :query-suggestions="querySuggestions"
        :resolve-attribute-type="resolveAttributeType"
      />
    `
  })
  const wrapper = mount(wrapperComponent, attach ? { attachTo: document.body } : {})
  return { wrapper, model }
}

test('picking a known key applies key and inferred attributeType in one mutation', async () => {
  const { wrapper, model } = mountForm(makeModel(), (key) =>
    key === 'http.method' ? 'datapoint' : null
  )
  const pills = wrapper.findAllComponents(AttributeFilterPill)
  // The pill emits only `update:key`; the parent owns the resolver and merges
  // the inferred attributeType into the same model mutation. A regression that
  // re-splits this into two sequential emits would let the second write
  // overwrite the first via `defineModel`'s deferred prop propagation.
  pills[0]!.vm.$emit('update:key', 'http.method')
  await wrapper.vm.$nextTick()

  expect(model.value[0]).toMatchObject({
    id: 'pill-a',
    key: 'http.method',
    attributeType: 'datapoint'
  })
  // Pill B must be untouched — guards against any cross-row contamination
  // that a sloppier identity strategy could introduce.
  expect(model.value[1]).toMatchObject({
    id: 'pill-b',
    key: 'otel.library.name',
    attributeType: 'scope'
  })
})

test('picking a key without a resolver hit preserves the existing attributeType', async () => {
  // Seed pill-a with a non-null attributeType so the assertion exercises the
  // "no inference → leave the type alone" path. A free-text key edit on a
  // resolver-less form must not silently wipe a user-picked type.
  const initial = makeModel()
  initial[0]!.attributeType = 'resource'
  initial[0]!.key = 'service.name'
  const { wrapper, model } = mountForm(initial)
  const pills = wrapper.findAllComponents(AttributeFilterPill)
  pills[0]!.vm.$emit('update:key', 'foo.bar')
  await wrapper.vm.$nextTick()

  expect(model.value[0]).toMatchObject({ key: 'foo.bar', attributeType: 'resource' })
})

test('manual attributeType change persists on the targeted row', async () => {
  const { wrapper, model } = mountForm(makeModel())
  const pills = wrapper.findAllComponents(AttributeFilterPill)
  pills[1]!.vm.$emit('update:attributeType', 'datapoint')
  await wrapper.vm.$nextTick()

  expect(model.value[1]!.attributeType).toBe('datapoint')
  expect(model.value[0]!.attributeType).toBe(null)
})

test('picking a key with no resolver hit auto-opens the type dropdown', async () => {
  const { wrapper } = mountForm(makeModel(), () => null, { attach: true })
  const pills = wrapper.findAllComponents(AttributeFilterPill)
  pills[0]!.vm.$emit('update:key', 'foo.bar')
  await flushPromises()

  const typeButton = pills[0]!.get('[aria-label="Attribute type"]')
  expect(typeButton.attributes('aria-expanded')).toBe('true')
  wrapper.unmount()
})

test('picking a key with a resolver hit does not auto-open the type dropdown', async () => {
  const { wrapper } = mountForm(
    makeModel(),
    (key) => (key === 'http.method' ? 'datapoint' : null),
    {
      attach: true
    }
  )
  const pills = wrapper.findAllComponents(AttributeFilterPill)
  pills[0]!.vm.$emit('update:key', 'http.method')
  await flushPromises()

  const typeButton = pills[0]!.get('[aria-label="Attribute type"]')
  expect(typeButton.attributes('aria-expanded')).toBe('false')
  wrapper.unmount()
})

test('remove drops the targeted row by id, leaving siblings intact', async () => {
  const { wrapper, model } = mountForm(makeModel())
  const pills = wrapper.findAllComponents(AttributeFilterPill)
  pills[0]!.vm.$emit('remove')
  await wrapper.vm.$nextTick()

  expect(model.value).toHaveLength(1)
  expect(model.value[0]!.id).toBe('pill-b')
})
