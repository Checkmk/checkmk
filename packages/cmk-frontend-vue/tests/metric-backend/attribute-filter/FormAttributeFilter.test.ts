/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { Response } from 'cmk-ui-library/components/CmkSuggestions/suggestions'
import { defineComponent, ref } from 'vue'

import FormAttributeFilter from '@/metric-backend/attribute-filter/FormAttributeFilter.vue'
import { pillLabel } from '@/metric-backend/attribute-filter/pill-label'
import type {
  AttributeFilterModel,
  AttributeKind,
  Condition,
  ConditionGroup,
  Operator
} from '@/metric-backend/attribute-filter/types'

const KEY_SUGGESTIONS = [
  { name: 'http.method', title: 'http.method' },
  { name: 'service.name', title: 'service.name' },
  { name: 'foo.bar', title: 'foo.bar' }
]

function condition(id: string, overrides: Partial<Condition> = {}): Condition {
  return { id, attributeKind: null, key: '', operator: 'eq', value: '', ...overrides }
}

function conditionGroup(id: string, ...conditions: Condition[]): ConditionGroup {
  return { id, conditions }
}

// Flat view for assertions that check condition fields or order, not grouping.
function conditionsOf(model: AttributeFilterModel): Condition[] {
  return model.flatMap((g) => g.conditions)
}

function makeModel(): AttributeFilterModel {
  return [
    conditionGroup('group-a', condition('pill-a')),
    conditionGroup(
      'group-b',
      condition('pill-b', { attributeKind: 'scope', key: 'otel.library.name' })
    )
  ]
}

function singlePill(overrides: Partial<Condition> = {}): AttributeFilterModel {
  return [
    conditionGroup(
      'group-a',
      condition('pill-a', { attributeKind: 'resource', key: 'service.name', ...overrides })
    )
  ]
}

function querySuggestions(query: string): Promise<Response> {
  const lower = query.toLowerCase()
  return Promise.resolve(
    new Response(KEY_SUGGESTIONS.filter((s) => s.name.toLowerCase().includes(lower)))
  )
}

function echoQueryValueSuggestions(_: unknown, query: string): Promise<Response> {
  return Promise.resolve(new Response(query ? [{ name: query, title: query }] : []))
}

function renderForm(
  initial: AttributeFilterModel,
  resolve?: (key: string) => AttributeKind,
  initialOperators?: Operator[],
  allowOr: boolean = true
): {
  model: ReturnType<typeof ref<AttributeFilterModel>>
  operators: ReturnType<typeof ref<Operator[] | undefined>>
} {
  const model = ref<AttributeFilterModel>(initial)
  const operators = ref<Operator[] | undefined>(initialOperators)
  const wrapperComponent = defineComponent({
    components: { FormAttributeFilter },
    setup() {
      return {
        model,
        operators,
        allowOr,
        querySuggestions,
        queryValueSuggestions: echoQueryValueSuggestions,
        resolveAttributeKind: resolve
      }
    },
    template: `
      <FormAttributeFilter
        v-model="model"
        :allow-or="allowOr"
        :operators="operators"
        :query-suggestions="querySuggestions"
        :query-value-suggestions="queryValueSuggestions"
        :resolve-attribute-kind="resolveAttributeKind"
      />
    `
  })
  render(wrapperComponent)
  return { model, operators }
}

function pillsInOrder(): HTMLElement[] {
  const outerGroup = screen.getByRole('group', { name: 'Attribute filter' })
  return within(outerGroup).getAllByRole('group')
}

async function enterEditMode(pill: HTMLElement): Promise<void> {
  const editButton = within(pill).queryByRole('button', { name: /^Edit condition:/ })
  if (editButton) {
    await userEvent.click(editButton)
  }
}

async function pickKey(pill: HTMLElement, name: string): Promise<void> {
  await enterEditMode(pill)
  // Let the empty-key auto-open (deferred to nextTick) settle so the click
  // below cannot toggle a just-opened dropdown closed again.
  await new Promise((resolve) => setTimeout(resolve, 0))
  const keyCombobox = within(pill).getByRole('combobox', { name: 'Attribute key' })
  if (keyCombobox.getAttribute('aria-expanded') !== 'true') {
    await userEvent.click(keyCombobox)
  }
  const filter = screen.getByRole('textbox', { name: 'filter' })
  // In callback-filtered mode the filter is pre-populated with the current
  // selection's title; clear it so the typed query starts from scratch.
  await userEvent.clear(filter)
  await userEvent.type(filter, name)
  await userEvent.click(await screen.findByRole('option', { name }))
}

async function pickOperator(pill: HTMLElement, phrase: string): Promise<void> {
  await enterEditMode(pill)
  const operatorCombobox = within(pill).getByRole('combobox', { name: 'Attribute operator' })
  await userEvent.click(operatorCombobox)
  await userEvent.click(await screen.findByRole('option', { name: phrase }))
}

async function pickAttributeKind(pill: HTMLElement, label: string): Promise<void> {
  await enterEditMode(pill)
  // Let any pending auto-open settle so the click below cannot toggle a
  // just-opened dropdown closed again.
  await new Promise((resolve) => setTimeout(resolve, 0))
  const kindCombobox = within(pill).getByRole('combobox', { name: 'Attribute kind' })
  if (kindCombobox.getAttribute('aria-expanded') !== 'true') {
    await userEvent.click(kindCombobox)
  }
  await userEvent.click(await screen.findByRole('option', { name: label }))
}

test('picking a known key applies key and inferred attributeKind in one mutation', async () => {
  const { model } = renderForm(makeModel(), (key) => (key === 'http.method' ? 'data_point' : null))
  // The pill emits only `update:key`; the parent owns the resolver and merges
  // the inferred attributeKind into the same model mutation. A regression that
  // re-splits this into two sequential emits would let the second write
  // overwrite the first via `defineModel`'s deferred prop propagation.
  await pickKey(pillsInOrder()[0]!, 'http.method')

  const conditions = conditionsOf(model.value!)
  expect(conditions[0]).toMatchObject({
    id: 'pill-a',
    key: 'http.method',
    attributeKind: 'data_point'
  })
  // Pill B must be untouched — guards against any cross-row contamination
  // that a sloppier identity strategy could introduce.
  expect(conditions[1]).toMatchObject({
    id: 'pill-b',
    key: 'otel.library.name',
    attributeKind: 'scope'
  })
})

test('picking a key without a resolver hit preserves the existing attributeKind', async () => {
  // Seed pill-a with a non-null attributeKind so the assertion exercises the
  // "no inference → leave the type alone" path. A free-text key edit on a
  // resolver-less form must not silently wipe a user-picked type.
  const initial = makeModel()
  initial[0]!.conditions[0]!.attributeKind = 'resource'
  initial[0]!.conditions[0]!.key = 'service.name'
  const { model } = renderForm(initial)
  await pickKey(pillsInOrder()[0]!, 'foo.bar')

  expect(conditionsOf(model.value!)[0]).toMatchObject({ key: 'foo.bar', attributeKind: 'resource' })
})

test('manual attributeKind change persists on the targeted row', async () => {
  const { model } = renderForm(makeModel())
  await pickAttributeKind(pillsInOrder()[1]!, 'Data point')

  const conditions = conditionsOf(model.value!)
  expect(conditions[1]!.attributeKind).toBe('data_point')
  expect(conditions[0]!.attributeKind).toBe(null)
})

test('manual operator change persists on the targeted row', async () => {
  const { model } = renderForm(makeModel())
  await pickOperator(pillsInOrder()[1]!, 'is not')

  const conditions = conditionsOf(model.value!)
  expect(conditions[1]!.operator).toBe('neq')
  expect(conditions[0]!.operator).toBe('eq')
})

test('restricting operators to a single choice forces every pill onto it, not just the last', async () => {
  const { model, operators } = renderForm([
    conditionGroup(
      'g',
      condition('pill-a', { key: 'service.name', operator: 'eq', value: 'foo' }),
      condition('pill-b', { key: 'otel.library.name', operator: 'neq', value: 'bar' }),
      condition('pill-c', { key: 'http.method', operator: 'starts_with', value: 'baz' })
    )
  ])

  operators.value = ['contains']

  await waitFor(() => {
    expect(conditionsOf(model.value!).map((c) => c.operator)).toEqual([
      'contains',
      'contains',
      'contains'
    ])
  })
  // contains takes a value, so each populated value survives the coercion.
  expect(conditionsOf(model.value!).map((c) => c.value)).toEqual(['foo', 'bar', 'baz'])
})

test('forcing onto a single existence operator clears the value of every pill', async () => {
  const { model, operators } = renderForm([
    conditionGroup(
      'g',
      condition('pill-a', { key: 'service.name', operator: 'eq', value: 'foo' }),
      condition('pill-b', { key: 'http.method', operator: 'contains', value: 'bar' })
    )
  ])

  operators.value = ['exists']

  await waitFor(() => {
    expect(conditionsOf(model.value!).map((c) => c.operator)).toEqual(['exists', 'exists'])
  })
  expect(conditionsOf(model.value!).map((c) => c.value)).toEqual(['', ''])
})

test('picking a key with no resolver hit auto-opens the type dropdown', async () => {
  renderForm(makeModel(), () => null)
  const pillA = pillsInOrder()[0]!
  await pickKey(pillA, 'foo.bar')

  const kindCombobox = within(pillA).getByRole('combobox', { name: 'Attribute kind' })
  await waitFor(() => {
    expect(kindCombobox.getAttribute('aria-expanded')).toBe('true')
  })
})

test('picking a key with a resolver hit does not auto-open the type dropdown', async () => {
  renderForm(makeModel(), (key) => (key === 'http.method' ? 'data_point' : null))
  const pillA = pillsInOrder()[0]!
  await pickKey(pillA, 'http.method')

  const kindCombobox = within(pillA).getByRole('combobox', { name: 'Attribute kind' })
  // Give the watcher's nextTick a chance to run; aria-expanded must stay 'false'.
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(kindCombobox.getAttribute('aria-expanded')).toBe('false')
})

test('picking a key with a resolver hit auto-opens the value dropdown', async () => {
  renderForm(makeModel(), (key) => (key === 'http.method' ? 'data_point' : null))
  const pillA = pillsInOrder()[0]!
  await pickKey(pillA, 'http.method')

  const valueCombobox = within(pillA).getByRole('combobox', { name: 'Attribute value' })
  await waitFor(() => {
    expect(valueCombobox.getAttribute('aria-expanded')).toBe('true')
  })
})

test('picking the type after a no-hit key auto-opens the value dropdown', async () => {
  renderForm(makeModel(), () => null)
  const pillA = pillsInOrder()[0]!
  await pickKey(pillA, 'foo.bar')
  await pickAttributeKind(pillA, 'Resource')

  const valueCombobox = within(pillA).getByRole('combobox', { name: 'Attribute value' })
  await waitFor(() => {
    expect(valueCombobox.getAttribute('aria-expanded')).toBe('true')
  })
})

test('picking a suggestion leaves the pill in edit mode', async () => {
  const { model } = renderForm(singlePill())
  const pill = pillsInOrder()[0]!
  await enterEditMode(pill)

  await userEvent.click(within(pill).getByRole('combobox', { name: 'Attribute value' }))
  await userEvent.type(screen.getByRole('textbox', { name: 'filter' }), 'prod')
  await userEvent.click(await screen.findByRole('option', { name: 'prod' }))

  await waitFor(() => expect(conditionsOf(model.value!)[0]).toMatchObject({ value: 'prod' }))
  expect(within(pill).queryByRole('button', { name: /^Edit condition:/ })).toBeNull()
  expect(within(pill).getByRole('combobox', { name: 'Attribute value' })).toBeVisible()
})

test('a newly added pill auto-opens the key dropdown', async () => {
  renderForm([])
  await userEvent.click(screen.getByRole('button', { name: 'Add condition' }))

  const keyCombobox = within(pillsInOrder()[0]!).getByRole('combobox', { name: 'Attribute key' })
  await waitFor(() => {
    expect(keyCombobox.getAttribute('aria-expanded')).toBe('true')
  })
})

test('editing an existing pill does not auto-open the key dropdown', async () => {
  renderForm(singlePill())
  const pill = pillsInOrder()[0]!
  await enterEditMode(pill)

  const keyCombobox = within(pill).getByRole('combobox', { name: 'Attribute key' })
  // Give the watcher's nextTick a chance to run; aria-expanded must stay 'false'.
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(keyCombobox.getAttribute('aria-expanded')).toBe('false')
})

test('removing the head drops it by id and leaves the next group', async () => {
  const { model } = renderForm(makeModel())
  const pillA = pillsInOrder()[0]!
  const pillALabel = pillLabel(conditionsOf(makeModel())[0]!)
  await userEvent.click(within(pillA).getByRole('button', { name: 'Remove condition' }))

  expect(conditionsOf(model.value!).map((c) => c.id)).toEqual(['pill-b'])
  // The removed pill must be gone from the DOM, not just from the model.
  expect(screen.queryByRole('group', { name: pillALabel })).toBeNull()
})

test('empty-state add button creates a single row with documented defaults', async () => {
  const { model } = renderForm([])
  await userEvent.click(screen.getByRole('button', { name: 'Add condition' }))

  const conditions = conditionsOf(model.value!)
  expect(conditions).toHaveLength(1)
  expect(conditions[0]).toMatchObject({ attributeKind: null, key: '', operator: 'eq', value: '' })
  expect(conditions[0]!.id).toEqual(expect.any(String))
  expect(conditions[0]!.id.length).toBeGreaterThan(0)
})

test('per-pill add button inserts a fresh AND-joined row after it, leaving the other clause intact', async () => {
  const { model } = renderForm(makeModel())
  await userEvent.click(
    screen.getByRole('button', { name: 'Add condition after previous condition' })
  )

  // makeModel is two OR clauses; adding defaults to AND, so the first clause
  // grows to two conditions and the second OR clause is left untouched.
  expect(model.value).toHaveLength(2)
  expect(model.value![0]!.conditions.map((c) => c.id)).toEqual(['pill-a', expect.any(String)])
  expect(model.value![1]!.conditions.map((c) => c.id)).toEqual(['pill-b'])
  const fresh = model.value![0]!.conditions[1]!
  expect(fresh).toMatchObject({ attributeKind: null, key: '', operator: 'eq', value: '' })
  expect(fresh.id).toEqual(expect.any(String))
  expect(fresh.id).not.toBe('pill-a')
  expect(fresh.id).not.toBe('pill-b')
})

test('value is preserved when switching between two comparison operators', async () => {
  const { model } = renderForm(singlePill({ operator: 'eq', value: 'foo' }))

  await pickOperator(pillsInOrder()[0]!, 'starts with')

  expect(conditionsOf(model.value!)[0]).toMatchObject({ operator: 'starts_with', value: 'foo' })
  expect(screen.getByRole('combobox', { name: 'Attribute value' })).toHaveTextContent('foo')
})

test('value is cleared when switching to an existence operator and stays empty on return', async () => {
  const { model } = renderForm(singlePill({ operator: 'eq', value: 'foo' }))

  await pickOperator(pillsInOrder()[0]!, 'exists')

  expect(conditionsOf(model.value!)[0]).toMatchObject({ operator: 'exists', value: '' })
  expect(screen.queryByRole('combobox', { name: 'Attribute value' })).toBeNull()

  await pickOperator(pillsInOrder()[0]!, 'is')

  expect(conditionsOf(model.value!)[0]).toMatchObject({ operator: 'eq', value: '' })
})

test('switching from an existence operator to a value-taking operator auto-opens the value dropdown', async () => {
  renderForm(singlePill({ operator: 'exists', value: '' }))

  await pickOperator(pillsInOrder()[0]!, 'is')

  expect(screen.getByRole('combobox', { name: 'Attribute value' })).toHaveAttribute(
    'aria-expanded',
    'true'
  )
})

test('same-family swap with a populated value does not auto-open the value dropdown', async () => {
  renderForm(singlePill({ operator: 'eq', value: 'foo' }))

  await pickOperator(pillsInOrder()[0]!, 'starts with')

  expect(screen.getByRole('combobox', { name: 'Attribute value' })).toHaveAttribute(
    'aria-expanded',
    'false'
  )
})

test('same-family swap with an empty value auto-opens the value dropdown', async () => {
  renderForm(singlePill({ operator: 'eq', value: '' }))

  await pickOperator(pillsInOrder()[0]!, 'starts with')

  expect(screen.getByRole('combobox', { name: 'Attribute value' })).toHaveAttribute(
    'aria-expanded',
    'true'
  )
})

const ERROR_CLASS = 'cmk-dropdown__validation-error'

const FIELD_LABELS = ['Attribute kind', 'Attribute key', 'Attribute operator', 'Attribute value']

function field(pill: HTMLElement, label: string): HTMLElement {
  return within(pill).getByRole('combobox', { name: label })
}

describe('pill required-field validation', () => {
  test('an unedited pill shows no validation errors', async () => {
    renderForm(makeModel())
    const pill = pillsInOrder()[0]!
    await enterEditMode(pill)
    // 'Attribute kind' is excluded: it is hidden while the key is empty.
    for (const label of ['Attribute key', 'Attribute operator', 'Attribute value']) {
      expect(field(pill, label)).not.toHaveClass(ERROR_CLASS)
    }
  })

  test('the type dropdown is hidden until a key is chosen', async () => {
    renderForm(makeModel())
    const pill = pillsInOrder()[0]!
    await enterEditMode(pill)
    expect(within(pill).queryByRole('combobox', { name: 'Attribute kind' })).toBeNull()
  })

  test('a partly-filled but uncommitted pill flags nothing', async () => {
    renderForm(makeModel())
    const pill = pillsInOrder()[1]!
    await enterEditMode(pill)
    for (const label of FIELD_LABELS) {
      expect(field(pill, label)).not.toHaveClass(ERROR_CLASS)
      expect(field(pill, label)).not.toHaveTextContent('(required)')
    }
  })

  test('picking a key does not reveal validation on the still-empty type', async () => {
    const { model } = renderForm(makeModel(), () => null)
    await pickKey(pillsInOrder()[0]!, 'http.method')

    expect(conditionsOf(model.value!)[0]!.key).toBe('http.method')
    const pill = pillsInOrder()[0]!
    for (const label of ['Attribute kind', 'Attribute key']) {
      expect(field(pill, label)).not.toHaveClass(ERROR_CLASS)
      expect(field(pill, label)).not.toHaveTextContent('(required)')
    }
  })
})

test('preloaded pills start in read-only mode', () => {
  renderForm(makeModel())
  expect(screen.getAllByRole('button', { name: /^Edit condition:/ })).toHaveLength(2)
  expect(screen.queryByRole('combobox', { name: 'Attribute operator' })).toBeNull()
})

test('clicking a read-only pill opens it for editing', async () => {
  renderForm(makeModel())
  const pillB = pillsInOrder()[1]!
  await enterEditMode(pillB)

  expect(within(pillB).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
  const pillA = pillsInOrder()[0]!
  expect(within(pillA).queryByRole('button', { name: /^Edit condition:/ })).not.toBeNull()
})

test('opening a second pill closes the previously open one', async () => {
  renderForm([
    conditionGroup(
      'g-a',
      condition('pill-a', { attributeKind: 'resource', key: 'service.name', value: 'foo' })
    ),
    conditionGroup(
      'g-b',
      condition('pill-b', { attributeKind: 'scope', key: 'otel.library.name', value: 'bar' })
    )
  ])
  await enterEditMode(pillsInOrder()[0]!)
  expect(
    within(pillsInOrder()[0]!).getByRole('combobox', { name: 'Attribute operator' })
  ).toBeInTheDocument()

  await enterEditMode(pillsInOrder()[1]!)
  expect(
    within(pillsInOrder()[1]!).getByRole('combobox', { name: 'Attribute operator' })
  ).toBeInTheDocument()
  expect(
    within(pillsInOrder()[0]!).queryByRole('combobox', { name: 'Attribute operator' })
  ).toBeNull()
})

test('removing the editing pill clears the editing state', async () => {
  const { model } = renderForm(makeModel())
  const pillA = pillsInOrder()[0]!
  await enterEditMode(pillA)
  await userEvent.click(within(pillA).getByRole('button', { name: 'Remove condition' }))

  expect(model.value).toHaveLength(1)
  const remaining = pillsInOrder()
  expect(remaining).toHaveLength(1)
  expect(within(remaining[0]!).queryByRole('button', { name: /^Edit condition:/ })).not.toBeNull()
  expect(within(remaining[0]!).queryByRole('combobox', { name: 'Attribute operator' })).toBeNull()
})

function dispatchOutsideClick(): void {
  document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

test('click outside closes a fully-valid edit pill back to read-only', async () => {
  renderForm([
    conditionGroup(
      'g',
      condition('pill-a', { attributeKind: 'scope', key: 'otel.library.name', value: 'foo' })
    )
  ])
  const pillA = pillsInOrder()[0]!
  await enterEditMode(pillA)
  expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()

  dispatchOutsideClick()
  await waitFor(() => {
    expect(within(pillA).queryByRole('combobox', { name: 'Attribute operator' })).toBeNull()
  })
})

test('click outside on a partly-filled invalid pill keeps it open and reveals errors', async () => {
  renderForm(singlePill({ key: 'service.name', value: '' }))
  const pillA = pillsInOrder()[0]!
  await enterEditMode(pillA)
  // Before the commit attempt, no field is flagged.
  expect(field(pillA, 'Attribute value')).not.toHaveClass(ERROR_CLASS)

  dispatchOutsideClick()
  expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
  await waitFor(() => {
    expect(field(pillA, 'Attribute value')).toHaveClass(ERROR_CLASS)
  })
})

test('click outside on a pristine invalid pill keeps it open and reveals errors', async () => {
  renderForm(makeModel())
  const pillA = pillsInOrder()[0]!
  await enterEditMode(pillA)

  dispatchOutsideClick()
  expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
  await waitFor(() => {
    expect(field(pillA, 'Attribute key')).toHaveClass(ERROR_CLASS)
  })
  expect(field(pillA, 'Attribute value')).toHaveClass(ERROR_CLASS)
})

describe('Escape in edit mode', () => {
  function focusOperator(pill: HTMLElement): void {
    within(pill).getByRole('combobox', { name: 'Attribute operator' }).focus()
  }

  function focusRemoveX(pill: HTMLElement): void {
    within(pill).getByRole('button', { name: 'Remove condition' }).focus()
  }

  test.each([
    ['the operator combobox', focusOperator],
    ['the remove X', focusRemoveX]
  ])(
    'Escape on a valid editing pill from %s commits and focuses the combined Tab stop',
    async (_name, focusFn) => {
      renderForm([
        conditionGroup(
          'g',
          condition('pill-a', { attributeKind: 'scope', key: 'otel.library.name', value: 'foo' })
        )
      ])
      const pillA = pillsInOrder()[0]!
      await enterEditMode(pillA)
      focusFn(pillA)

      await userEvent.keyboard('{Escape}')

      await waitFor(() => {
        expect(within(pillA).queryByRole('combobox', { name: 'Attribute operator' })).toBeNull()
      })
      await waitFor(() => {
        const focused = document.activeElement as HTMLElement
        expect(pillA.contains(focused)).toBe(true)
        expect(
          within(focused).getByRole('button', { name: /^Edit condition:/ })
        ).toBeInTheDocument()
        expect(
          within(focused).getByRole('button', { name: 'Remove condition' })
        ).toBeInTheDocument()
      })
    }
  )

  test('Escape on an invalid editing pill keeps it open and reveals errors', async () => {
    renderForm(singlePill({ key: 'service.name', value: '' }))
    const pillA = pillsInOrder()[0]!
    await enterEditMode(pillA)
    focusOperator(pillA)

    await userEvent.keyboard('{Escape}')

    expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
    await waitFor(() => {
      expect(field(pillA, 'Attribute value')).toHaveClass(ERROR_CLASS)
    })
  })

  test('Escape with a dropdown open only closes the dropdown', async () => {
    renderForm([
      conditionGroup(
        'g',
        condition('pill-a', { attributeKind: 'scope', key: 'otel.library.name', value: 'foo' })
      )
    ])
    const pillA = pillsInOrder()[0]!
    await enterEditMode(pillA)
    const operatorCombobox = within(pillA).getByRole('combobox', { name: 'Attribute operator' })
    await userEvent.click(operatorCombobox)
    await waitFor(() => {
      expect(operatorCombobox).toHaveAttribute('aria-expanded', 'true')
    })

    await userEvent.keyboard('{Escape}')

    await waitFor(() => {
      expect(operatorCombobox).toHaveAttribute('aria-expanded', 'false')
    })
    expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
  })
})

describe('combined pill keyboard stop', () => {
  function chipOf(pill: HTMLElement): HTMLElement {
    return within(pill).getByRole('button', { name: /^Edit condition:/ })
  }

  test('closed: tabbing into the pill lands on a single stop that wraps the chip and the remove X', async () => {
    renderForm(makeModel())
    const pillA = pillsInOrder()[0]!

    for (let i = 0; i < 20 && !pillA.contains(document.activeElement); i++) {
      await userEvent.tab()
    }

    const focused = document.activeElement as HTMLElement
    expect(pillA.contains(focused)).toBe(true)
    expect(within(focused).getByRole('button', { name: /^Edit condition:/ })).toBeInTheDocument()
    expect(within(focused).getByRole('button', { name: 'Remove condition' })).toBeInTheDocument()
  })

  test('edit mode: tabbing forward eventually focuses the remove X on its own', async () => {
    renderForm(makeModel())
    const pillA = pillsInOrder()[0]!
    await enterEditMode(pillA)
    const removeX = within(pillA).getByRole('button', { name: 'Remove condition' })

    for (let i = 0; i < 20 && document.activeElement !== removeX; i++) {
      await userEvent.tab()
    }

    expect(document.activeElement).toBe(removeX)
  })

  test.each([
    ['Backspace', '{Backspace}'],
    ['Delete', '{Delete}']
  ])('%s on a focused chip removes the pill', async (_name, key) => {
    const { model } = renderForm(makeModel())
    chipOf(pillsInOrder()[0]!).focus()

    await userEvent.keyboard(key)

    expect(conditionsOf(model.value!).map((c) => c.id)).toEqual(['pill-b'])
  })

  test.each([
    ['Space', ' '],
    ['Enter', '{Enter}']
  ])('%s on a focused chip enters edit mode', async (_name, key) => {
    renderForm(makeModel())
    const pillA = pillsInOrder()[0]!
    chipOf(pillA).focus()

    await userEvent.keyboard(key)

    expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
  })

  test.each([
    ['Space', ' '],
    ['Enter', '{Enter}']
  ])(
    '%s on a focused chip of a populated pill focuses the first inline dropdown without opening it',
    async (_name, key) => {
      // pill-b is the populated read-only pill in the standard fixture: it has
      // both attributeKind and key set, so the attribute-kind dropdown is
      // visible and is the first dropdown in DOM order.
      renderForm(makeModel())
      const pillB = pillsInOrder()[1]!
      chipOf(pillB).focus()

      await userEvent.keyboard(key)

      const firstDropdown = within(pillB).getByRole('combobox', { name: 'Attribute kind' })
      await waitFor(() => expect(document.activeElement).toBe(firstDropdown))
      expect(firstDropdown).toHaveAttribute('aria-expanded', 'false')
    }
  )

  test('Tab from a chip lands on the per-pill +, skipping the remove X', async () => {
    renderForm(makeModel())
    chipOf(pillsInOrder()[0]!).focus()

    await userEvent.tab()

    expect(
      screen.getByRole('button', { name: 'Add condition after previous condition' })
    ).toHaveFocus()
  })
})

describe('combined group keyboard stop', () => {
  const TWO_PILL_AND = [conditionGroup('g', condition('pill-a'), condition('pill-b'))]

  function groupWrapper(): HTMLElement {
    return screen.getByTestId(GROUP_TESTID)
  }

  async function expandGroup(): Promise<HTMLElement> {
    const group = groupWrapper()
    group.focus()
    await userEvent.keyboard(' ')
    return group
  }

  test('closed: tabbing into a multi-pill group lands on a single stop that wraps the chips, +s, connector, and the remove X', async () => {
    renderForm(TWO_PILL_AND)
    const group = groupWrapper()

    for (let i = 0; i < 20 && !group.contains(document.activeElement); i++) {
      await userEvent.tab()
    }

    const focused = document.activeElement as HTMLElement
    expect(group.contains(focused)).toBe(true)
    expect(within(focused).getByRole('button', { name: 'Remove group' })).toBeInTheDocument()
    expect(within(focused).getAllByRole('button', { name: /^Edit condition:/ })).toHaveLength(2)
    expect(
      within(focused).getAllByRole('button', { name: /^Add condition after / }).length
    ).toBeGreaterThan(0)
    expect(
      within(focused).getByRole('button', { name: /^Toggle connector, currently / })
    ).toBeInTheDocument()
  })

  test.each([
    ['Backspace', '{Backspace}'],
    ['Delete', '{Delete}']
  ])('%s on the focused group removes the group', async (_name, key) => {
    const { model } = renderForm(TWO_PILL_AND)
    groupWrapper().focus()

    await userEvent.keyboard(key)

    expect(model.value).toEqual([])
  })

  test.each([
    ['Space', ' '],
    ['Enter', '{Enter}']
  ])('%s on the focused group expands it and focuses the first pill', async (_name, key) => {
    renderForm(TWO_PILL_AND)
    const group = groupWrapper()
    group.focus()

    await userEvent.keyboard(key)

    const firstPill = within(group).getAllByRole('group')[0]!
    expect(firstPill.contains(document.activeElement)).toBe(true)
    expect(document.activeElement).toHaveAttribute('tabindex', '0')
  })

  test('expanded: shift-tabbing from the first pill focuses the remove group X on its own', async () => {
    renderForm(TWO_PILL_AND)
    const group = await expandGroup()
    const removeX = within(group).getByRole('button', { name: 'Remove group' })

    await userEvent.tab({ shift: true })

    expect(document.activeElement).toBe(removeX)
  })

  test('expanded: tabbing out of the group does not collapse it', async () => {
    renderForm(TWO_PILL_AND)
    const group = await expandGroup()
    const removeX = within(group).getByRole('button', { name: 'Remove group' })

    for (let i = 0; i < 20 && group.contains(document.activeElement); i++) {
      await userEvent.tab()
    }

    expect(group.contains(document.activeElement)).toBe(false)
    expect(group).toHaveAttribute('tabindex', '-1')
    expect(removeX).toHaveAttribute('tabindex', '0')
  })

  test('expanded: clicking outside the group collapses it back to one Tab stop', async () => {
    renderForm(TWO_PILL_AND)
    const group = await expandGroup()

    dispatchOutsideClick()

    await waitFor(() => {
      expect(group).toHaveAttribute('tabindex', '0')
    })
    expect(within(group).getByRole('button', { name: 'Remove group' })).toHaveAttribute(
      'tabindex',
      '-1'
    )
  })

  test('expanded: Escape on the focused pill collapses the group and refocuses the wrapper', async () => {
    renderForm(TWO_PILL_AND)
    const group = await expandGroup()

    await userEvent.keyboard('{Escape}')

    expect(group).toHaveAttribute('tabindex', '0')
    expect(group).toHaveFocus()
  })

  test('expanded: Escape on an editing pill closes the pill but keeps the group entered', async () => {
    // Pre-fill the pills so entering edit mode does not auto-open the key
    // dropdown; otherwise the first Escape would just close that dropdown.
    renderForm([
      conditionGroup(
        'g',
        condition('pill-a', { attributeKind: 'resource', key: 'service.name', value: 'x' }),
        condition('pill-b', { attributeKind: 'resource', key: 'foo.bar', value: 'y' })
      )
    ])
    const group = await expandGroup()
    const pillA = pillsInOrder()[0]!
    await enterEditMode(pillA)
    within(pillA).getByRole('combobox', { name: 'Attribute operator' }).focus()

    await userEvent.keyboard('{Escape}')

    await waitFor(() => {
      expect(within(pillA).queryByRole('combobox', { name: 'Attribute operator' })).toBeNull()
    })
    expect(group).toHaveAttribute('tabindex', '-1')
    expect(within(group).getByRole('button', { name: 'Remove group' })).toHaveAttribute(
      'tabindex',
      '0'
    )
  })
})

describe('arrow-nav within multi-element stops', () => {
  const TWO_PILL_AND = [conditionGroup('g', condition('pill-a'), condition('pill-b'))]

  async function expand(): Promise<HTMLElement> {
    const group = screen.getByTestId(GROUP_TESTID)
    group.focus()
    await userEvent.keyboard(' ')
    return group
  }

  const TAB_STOP_SELECTOR = 'button, [role="combobox"], [tabindex="0"]'
  function tabStops(scope: HTMLElement): HTMLElement[] {
    return Array.from(scope.querySelectorAll<HTMLElement>(TAB_STOP_SELECTOR)).filter(
      (el) => el.getAttribute('tabindex') !== '-1'
    )
  }

  const cycleCases = [
    { key: 'ArrowRight', focusOrder: (items: HTMLElement[]) => [...items.slice(1), items[0]!] },
    {
      key: 'ArrowLeft',
      focusOrder: (items: HTMLElement[]) => [...items.slice(1).reverse(), items[0]!]
    }
  ]

  test.each(cycleCases)(
    '$key cycles inner controls from the group-entry stop and wraps, staying inside the group',
    async ({ key, focusOrder }) => {
      renderForm(TWO_PILL_AND)
      const group = await expand()
      const items = tabStops(group)
      expect(items.length).toBeGreaterThanOrEqual(2)
      // Group entry focuses the first pill's chip, not items[0]; cycle from that natural stop.
      const entryStop = document.activeElement as HTMLElement
      const startIdx = items.indexOf(entryStop)
      expect(startIdx).toBeGreaterThanOrEqual(0)
      const fromEntry = [...items.slice(startIdx), ...items.slice(0, startIdx)]

      for (const expected of focusOrder(fromEntry)) {
        await userEvent.keyboard(`{${key}}`)
        expect(expected).toHaveFocus()
        expect(group.contains(document.activeElement)).toBe(true)
      }
    }
  )

  test.each(cycleCases)(
    '$key cycles inner controls in DOM order and wraps, staying inside the pill',
    async ({ key, focusOrder }) => {
      // Pre-fill so entering edit mode does not auto-open the key dropdown.
      renderForm([
        conditionGroup(
          'g',
          condition('pill-a', { attributeKind: 'resource', key: 'service.name', value: 'x' }),
          condition('pill-b', { attributeKind: 'resource', key: 'foo.bar', value: 'y' })
        )
      ])
      await expand()
      const pillA = pillsInOrder()[0]!
      await enterEditMode(pillA)
      const items = tabStops(pillA)
      expect(items.length).toBeGreaterThanOrEqual(2)
      items[0]!.focus()

      for (const expected of focusOrder(items)) {
        await userEvent.keyboard(`{${key}}`)
        expect(expected).toHaveFocus()
        expect(pillA.contains(document.activeElement)).toBe(true)
      }
    }
  )

  test('arrows on a singleton pill chip are no-ops', async () => {
    renderForm(singlePill())
    const chip = screen.getByRole('button', { name: /^Edit condition:/ })
    chip.focus()

    await userEvent.keyboard('{ArrowRight}')

    expect(chip).toHaveFocus()
  })
})

test("clicking another pill's chip while the editing pill is invalid is a no-op and reveals errors", async () => {
  renderForm(makeModel())
  const pillA = pillsInOrder()[0]!
  const pillB = pillsInOrder()[1]!
  await enterEditMode(pillA)

  const pillBEditButton = within(pillB).getByRole('button', { name: /^Edit condition:/ })
  await userEvent.click(pillBEditButton)

  expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
  expect(field(pillA, 'Attribute key')).toHaveClass(ERROR_CLASS)
  expect(field(pillA, 'Attribute value')).toHaveClass(ERROR_CLASS)
  expect(within(pillB).queryByRole('combobox', { name: 'Attribute operator' })).toBeNull()
  expect(within(pillB).queryByRole('button', { name: /^Edit condition:/ })).not.toBeNull()
})

test("newly added pill via '+' starts in edit mode", async () => {
  const { model } = renderForm(makeModel())
  await userEvent.click(
    screen.getByRole('button', { name: 'Add condition after previous condition' })
  )

  // group-a gains the fresh AND-joined pill; the two originals stay read-only.
  expect(model.value).toHaveLength(2)
  expect(conditionsOf(model.value!)).toHaveLength(3)
  expect(screen.getAllByRole('combobox', { name: 'Attribute operator' })).toHaveLength(1)
  expect(screen.getAllByRole('button', { name: /^Edit condition:/ })).toHaveLength(2)
})

test("a freshly added pill via '+' does not display validation errors", async () => {
  renderForm(makeModel())
  await userEvent.click(
    screen.getByRole('button', { name: 'Add condition after previous condition' })
  )

  // The fresh pill is the only one in edit mode, so its fields are the only comboboxes.
  for (const label of ['Attribute key', 'Attribute operator', 'Attribute value']) {
    const combobox = screen.getByRole('combobox', { name: label })
    expect(combobox).not.toHaveClass(ERROR_CLASS)
    expect(combobox).not.toHaveTextContent('(required)')
  }
})

test('opening a sibling dropdown closes the previously-open one within the same pill', async () => {
  renderForm(singlePill({ key: 'service.name', value: 'foo' }))
  const pill = pillsInOrder()[0]!
  await enterEditMode(pill)

  const keyCombobox = within(pill).getByRole('combobox', { name: 'Attribute key' })
  const operatorCombobox = within(pill).getByRole('combobox', { name: 'Attribute operator' })

  await userEvent.click(keyCombobox)
  expect(keyCombobox).toHaveAttribute('aria-expanded', 'true')

  await userEvent.click(operatorCombobox)
  await waitFor(() => {
    expect(keyCombobox).toHaveAttribute('aria-expanded', 'false')
  })
  expect(operatorCombobox).toHaveAttribute('aria-expanded', 'true')
})

test('connector renders as a toggle button between adjacent pills', () => {
  renderForm([
    conditionGroup(
      'g-a',
      condition('pill-a', { attributeKind: 'resource', key: 'service.name', value: 'web-01' })
    ),
    conditionGroup(
      'g-b',
      condition('pill-b', {
        attributeKind: 'scope',
        key: 'otel.library.name',
        operator: 'contains',
        value: 'api'
      })
    )
  ])
  const connectors = screen.getAllByRole('button', {
    name: /^Toggle connector, currently /
  })
  expect(connectors).toHaveLength(1)
  expect(connectors[0]).toHaveTextContent('OR')
  expect(connectors[0]).toHaveAccessibleName('Toggle connector, currently OR')
})

test('clicking an OR connector merges the two clauses into one AND group', async () => {
  const { model } = renderForm([
    conditionGroup('g-a', condition('pill-a')),
    conditionGroup('g-b', condition('pill-b'))
  ])
  await userEvent.click(screen.getByRole('button', { name: 'Toggle connector, currently OR' }))

  expect(model.value).toHaveLength(1)
  expect(conditionsOf(model.value!).map((c) => c.id)).toEqual(['pill-a', 'pill-b'])
  expect(screen.getByRole('button', { name: 'Toggle connector, currently AND' })).toHaveTextContent(
    'AND'
  )
})

test('merging then splitting again returns to two OR clauses', async () => {
  const { model } = renderForm([
    conditionGroup('g-a', condition('pill-a')),
    conditionGroup('g-b', condition('pill-b'))
  ])
  await userEvent.click(screen.getByRole('button', { name: /^Toggle connector, currently / }))
  await userEvent.click(screen.getByRole('button', { name: /^Toggle connector, currently / }))

  expect(model.value).toHaveLength(2)
})

test('merging one OR boundary leaves the other intact', async () => {
  const { model } = renderForm([
    conditionGroup('g-a', condition('pill-a')),
    conditionGroup('g-b', condition('pill-b')),
    conditionGroup('g-c', condition('pill-c'))
  ])
  const firstConnector = screen.getAllByRole('button', {
    name: /^Toggle connector, currently /
  })[0]!
  await userEvent.click(firstConnector)

  expect(model.value![0]!.conditions.map((c) => c.id)).toEqual(['pill-a', 'pill-b'])
  expect(model.value![1]!.conditions.map((c) => c.id)).toEqual(['pill-c'])
  // The OR boundary before pill-c is untouched.
  expect(screen.getByRole('button', { name: 'Toggle connector, currently OR' })).toBeInTheDocument()
})

test('head pill has no connector toggle button', () => {
  renderForm([conditionGroup('g', condition('pill-a'))])
  expect(screen.queryByRole('button', { name: /^Toggle connector, currently / })).toBeNull()
})

const GROUP_TESTID = 'attribute-filter-group'

test('two AND-joined pills render inside one bordered group', () => {
  renderForm([conditionGroup('g', condition('pill-a'), condition('pill-b'))])
  const groups = screen.getAllByTestId(GROUP_TESTID)
  expect(groups).toHaveLength(1)
  expect(within(groups[0]!).getAllByRole('group')).toHaveLength(2)
  expect(
    within(groups[0]!).getByRole('button', { name: 'Toggle connector, currently AND' })
  ).toBeInTheDocument()
})

test('OR splits the pills into two bordered groups with OR outside both', () => {
  renderForm([
    conditionGroup('g1', condition('pill-a'), condition('pill-b')),
    conditionGroup('g2', condition('pill-c'), condition('pill-d'))
  ])
  const groups = screen.getAllByTestId(GROUP_TESTID)
  expect(groups).toHaveLength(2)
  expect(within(groups[0]!).getAllByRole('group')).toHaveLength(2)
  expect(within(groups[1]!).getAllByRole('group')).toHaveLength(2)
  expect(
    within(groups[0]!).queryByRole('button', { name: 'Toggle connector, currently OR' })
  ).toBeNull()
  expect(
    within(groups[1]!).queryByRole('button', { name: 'Toggle connector, currently OR' })
  ).toBeNull()
  expect(screen.getByRole('button', { name: 'Toggle connector, currently OR' })).toBeInTheDocument()
})

test('toggling AND to OR splits a 3-pill group into a pair and a lone pill', async () => {
  renderForm([conditionGroup('g', condition('pill-a'), condition('pill-b'), condition('pill-c'))])
  expect(screen.getAllByTestId(GROUP_TESTID)).toHaveLength(1)
  const ands = screen.getAllByRole('button', { name: 'Toggle connector, currently AND' })
  expect(ands).toHaveLength(2)
  await userEvent.click(ands[1]!)

  const groups = screen.getAllByTestId(GROUP_TESTID)
  expect(groups).toHaveLength(1)
  expect(within(groups[0]!).getAllByRole('group')).toHaveLength(2)
  expect(pillsInOrder()).toHaveLength(3)
})

test('every pill in an AND group has a per-pill + that inserts an AND pill at that position', async () => {
  const { model } = renderForm([
    conditionGroup(
      'g',
      condition('pill-a', { attributeKind: 'resource', key: 'service.name' }),
      condition('pill-b', { attributeKind: 'scope', key: 'otel.library.name' })
    )
  ])
  await userEvent.click(screen.getByRole('button', { name: 'Add condition after service.name' }))

  expect(model.value).toHaveLength(1)
  expect(conditionsOf(model.value!).map((c) => c.id)).toEqual([
    'pill-a',
    expect.any(String),
    'pill-b'
  ])
  const groups = screen.getAllByTestId(GROUP_TESTID)
  expect(groups).toHaveLength(1)
  expect(within(groups[0]!).getAllByRole('group')).toHaveLength(3)
})

test('the after-group + (outside the box) starts a new OR clause that renders as a bare pill', async () => {
  const { model } = renderForm([
    conditionGroup(
      'g',
      condition('pill-a', { attributeKind: 'resource', key: 'service.name' }),
      condition('pill-b', { attributeKind: 'scope', key: 'otel.library.name' })
    )
  ])
  await userEvent.click(screen.getByRole('button', { name: 'Add condition after this group' }))

  expect(model.value).toHaveLength(2)
  expect(conditionsOf(model.value!)).toHaveLength(3)
  const groups = screen.getAllByTestId(GROUP_TESTID)
  expect(groups).toHaveLength(1)
  expect(within(groups[0]!).getAllByRole('group')).toHaveLength(2)
  expect(pillsInOrder()).toHaveLength(3)
})

test('the group X removes every pill in that AND group', async () => {
  const { model } = renderForm([conditionGroup('g', condition('pill-a'), condition('pill-b'))])
  await userEvent.click(screen.getByRole('button', { name: 'Remove group' }))

  expect(model.value).toEqual([])
  expect(screen.queryAllByTestId(GROUP_TESTID)).toHaveLength(0)
})

test('removing the first of two OR groups leaves the second as the only group', async () => {
  const { model } = renderForm([
    conditionGroup('g1', condition('pill-a'), condition('pill-b')),
    conditionGroup('g2', condition('pill-c'), condition('pill-d'))
  ])
  const removeButtons = screen.getAllByRole('button', { name: 'Remove group' })
  expect(removeButtons).toHaveLength(2)
  await userEvent.click(removeButtons[0]!)

  expect(model.value).toHaveLength(1)
  expect(model.value![0]!.conditions.map((c) => c.id)).toEqual(['pill-c', 'pill-d'])
})

describe('AND-only mode (allowOr false)', () => {
  const TWO_PILL_AND = [conditionGroup('g', condition('pill-a'), condition('pill-b'))]

  test('renders flat pills with no group box and no connector toggles', () => {
    renderForm(TWO_PILL_AND, undefined, undefined, false)

    expect(screen.queryAllByTestId(GROUP_TESTID)).toHaveLength(0)
    expect(pillsInOrder()).toHaveLength(2)
    expect(screen.queryByRole('button', { name: /^Toggle connector, currently / })).toBeNull()
  })

  test('renders a static AND label between adjacent pills', () => {
    renderForm(TWO_PILL_AND, undefined, undefined, false)

    const outerGroup = screen.getByRole('group', { name: 'Attribute filter' })
    const connectors = within(outerGroup).getAllByText('AND')
    // One static label sits between the two pills; it is not a toggle button.
    expect(connectors).toHaveLength(1)
    expect(connectors[0]!.tagName).toBe('SPAN')
    expect(within(outerGroup).queryByRole('button', { name: /^Toggle connector/ })).toBeNull()
  })

  test('a single pill renders no connector label', () => {
    renderForm([conditionGroup('g', condition('pill-a'))], undefined, undefined, false)

    const outerGroup = screen.getByRole('group', { name: 'Attribute filter' })
    expect(within(outerGroup).queryByText('AND')).toBeNull()
  })

  test("per-pill '+' inserts an AND-connected pill at index + 1", async () => {
    const { model } = renderForm(
      [
        conditionGroup(
          'g',
          condition('pill-a', { attributeKind: 'resource', key: 'service.name' }),
          condition('pill-b', { attributeKind: 'scope', key: 'otel.library.name' })
        )
      ],
      undefined,
      undefined,
      false
    )
    await userEvent.click(screen.getByRole('button', { name: 'Add condition after service.name' }))

    expect(conditionsOf(model.value!).map((c) => c.id)).toEqual([
      'pill-a',
      expect.any(String),
      'pill-b'
    ])
  })
})
