/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { Response } from 'cmk-ui-library/components/CmkSuggestions/suggestions'
import { defineComponent, ref } from 'vue'

import AttributeFilterPill from '@/metric-backend/attribute-filter/AttributeFilterPill.vue'
import type { Condition, Operator } from '@/metric-backend/attribute-filter/types'

function noopQuerySuggestions(_: string): Promise<Response> {
  return Promise.resolve(new Response([]))
}

function echoQueryValueSuggestions(_: Condition, query: string): Promise<Response> {
  return Promise.resolve(new Response(query ? [{ name: query, title: query }] : []))
}

function renderPill(initialOperator: Operator = 'eq', value = 'GET', operators?: Operator[]) {
  const condition = ref<Condition>({
    id: 'pill',
    attributeKind: null,
    key: 'http.method',
    operator: initialOperator,
    value
  })
  const wrapper = defineComponent({
    components: { AttributeFilterPill },
    setup() {
      function onUpdateOperator(operator: Operator) {
        condition.value = { ...condition.value, operator }
      }
      function onUpdateValue(value: string) {
        condition.value = { ...condition.value, value }
      }
      return {
        condition,
        operators,
        onUpdateOperator,
        onUpdateValue,
        querySuggestions: noopQuerySuggestions,
        queryValueSuggestions: echoQueryValueSuggestions
      }
    },
    template: `
      <AttributeFilterPill
        :condition="condition"
        :operators="operators"
        editing
        :query-suggestions="querySuggestions"
        :query-value-suggestions="queryValueSuggestions"
        @update:operator="onUpdateOperator"
        @update:value="onUpdateValue"
      />
    `
  })
  render(wrapper)
  return { condition }
}

function renderClearablePill() {
  const condition = ref<Condition>({
    id: 'pill',
    attributeKind: 'resource',
    key: 'http.method',
    operator: 'eq',
    value: 'GET'
  })
  const wrapper = defineComponent({
    components: { AttributeFilterPill },
    setup() {
      return {
        condition,
        querySuggestions: noopQuerySuggestions,
        queryValueSuggestions: echoQueryValueSuggestions,
        onUpdateKey: (key: string) => (condition.value = { ...condition.value, key }),
        onUpdateValue: (value: string) => (condition.value = { ...condition.value, value })
      }
    },
    template: `
      <AttributeFilterPill
        :condition="condition"
        editing
        :query-suggestions="querySuggestions"
        :query-value-suggestions="queryValueSuggestions"
        @update:key="onUpdateKey"
        @update:value="onUpdateValue"
      />
    `
  })
  const { container } = render(wrapper)
  return { condition, container }
}

async function pickOperator(phrase: string): Promise<void> {
  await userEvent.click(screen.getByRole('combobox', { name: 'Attribute operator' }))
  await userEvent.click(await screen.findByRole('option', { name: phrase }))
}

test('selecting a comparison operator emits the new operator and keeps the value segment', async () => {
  const { condition } = renderPill('eq')
  await pickOperator('is not')

  expect(condition.value.operator).toBe('neq')
  await waitFor(() => expect(screen.getByLabelText('Attribute value')).toHaveTextContent('GET'))
})

test('a single allowed operator renders as static text in edit mode, not a dropdown', () => {
  renderPill('eq', 'GET', ['eq'])

  expect(screen.queryByRole('combobox', { name: 'Attribute operator' })).toBeNull()
  expect(screen.getByText('is')).toBeVisible()
})

test('selecting an existence operator hides the value segment, switching back restores it', async () => {
  const { condition } = renderPill('eq')

  await pickOperator('exists')
  expect(condition.value.operator).toBe('exists')
  expect(screen.queryByLabelText('Attribute value')).toBeNull()

  await pickOperator('is')
  expect(condition.value.operator).toBe('eq')
  await waitFor(() => expect(screen.getByLabelText('Attribute value')).toHaveTextContent('GET'))
})

test.each([
  { segment: 'key', expected: { key: '' } },
  { segment: 'value', expected: { value: '' } }
])('the clear button empties the $segment segment', async ({ segment, expected }) => {
  const { condition, container } = renderClearablePill()
  const segmentElement = container.querySelector<HTMLElement>(
    `.metric-backend-attribute-filter-pill__segment--${segment}`
  )!

  await userEvent.click(within(segmentElement).getByLabelText('Clear selection'))

  expect(condition.value).toMatchObject(expected)
})
