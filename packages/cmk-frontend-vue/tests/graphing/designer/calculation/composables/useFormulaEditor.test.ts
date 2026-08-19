/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { vi } from 'vitest'
import { type MaybeRefOrGetter, defineComponent, nextTick, ref } from 'vue'

import { useFormulaEditor } from '@/graphing/designer/calculation/composables/useFormulaEditor'
import type { GraphItem, ItemId } from '@/graphing/designer/types'

import { formulaItem, rrdMetricItem } from '../../fixtures'

const items: GraphItem[] = [rrdMetricItem('A'), rrdMetricItem('B')]

function mountEditor(
  editorItems: MaybeRefOrGetter<GraphItem[]> = () => items,
  editedItemId: ItemId | null = null
) {
  let api!: ReturnType<typeof useFormulaEditor>
  render(
    defineComponent({
      setup() {
        api = useFormulaEditor(editorItems, 'rrd', editedItemId)
        return () => null
      }
    })
  )
  return api
}

test('appendOperator appends the spaced symbol at the end', () => {
  const editor = mountEditor()
  editor.text.value = 'A'
  editor.appendOperator('*')
  expect(editor.text.value).toBe('A * ')
})

test('wrapFunction wraps the whole expression', () => {
  const editor = mountEditor()
  editor.text.value = 'A * B'
  editor.wrapFunction('avg')
  expect(editor.text.value).toBe('avg(A * B)')

  editor.reset()
  editor.wrapFunction('min')
  expect(editor.text.value).toBe('min()')
})

test('appendRef reuses the last operator, defaulting to +', () => {
  const editor = mountEditor()
  editor.text.value = 'A + B'
  editor.appendRef('C')
  expect(editor.text.value).toBe('A + B + C')

  editor.text.value = 'A * B'
  editor.appendRef('C')
  expect(editor.text.value).toBe('A * B * C')

  editor.reset()
  editor.appendRef('C')
  expect(editor.text.value).toBe('C')

  editor.text.value = 'A + '
  editor.appendRef('C')
  expect(editor.text.value).toBe('A + C')
})

test('appendRef inserts directly after an opening parenthesis', () => {
  const editor = mountEditor()
  editor.text.value = 'avg('
  editor.appendRef('C')
  expect(editor.text.value).toBe('avg(C')
})

test('commit returns the AST for a valid formula and errors otherwise', () => {
  const editor = mountEditor()
  editor.text.value = 'A'
  expect(editor.commit()).toEqual({ ast: { op: 'ref', id: 'A' } })

  editor.text.value = 'A +'
  const bad = editor.commit()
  expect('errors' in bad).toBe(true)
  if ('errors' in bad) {
    expect(bad.errors.length).toBeGreaterThan(0)
  }
})

test('commit reports an error for an empty formula', () => {
  const editor = mountEditor()
  const result = editor.commit()
  expect('errors' in result && result.errors).toEqual([
    'The formula is empty; add a metric id (e.g. A) or a number.'
  ])
  expect(editor.errors.value).toEqual([
    'The formula is empty; add a metric id (e.g. A) or a number.'
  ])

  editor.text.value = '   '
  const blank = editor.commit()
  expect('errors' in blank && blank.errors.length).toBeGreaterThan(0)
})

test('commit rejects a formula referencing the edited item itself', () => {
  const editor = mountEditor(() => [...items, formulaItem('F')], 'F')
  editor.text.value = 'F + 1'
  const result = editor.commit()
  expect('errors' in result && result.errors[0]).toContain('cannot reference itself')
})

test('commit rejects a reference cycle through another formula', () => {
  const cyclic = [...items, formulaItem('F'), formulaItem('G', { ast: { op: 'ref', id: 'F' } })]
  const editor = mountEditor(() => cyclic, 'F')
  editor.text.value = 'G + 1'
  const result = editor.commit()
  expect('errors' in result && result.errors[0]).toContain('circular reference')
})

test('shows errors only after the typing pause, and clears them as soon as they are resolved', async () => {
  vi.useFakeTimers()
  try {
    const editorItems = ref<GraphItem[]>([rrdMetricItem('A')])
    const editor = mountEditor(() => editorItems.value)

    editor.text.value = 'A + Z'
    await nextTick()
    vi.advanceTimersByTime(1400)
    expect(editor.errors.value).toEqual([])
    vi.advanceTimersByTime(100)
    expect(editor.errors.value).toEqual(['Unknown metric or formula "Z".'])

    editorItems.value = [...editorItems.value, rrdMetricItem('Z')]
    await nextTick()
    expect(editor.errors.value).toEqual([])
  } finally {
    vi.useRealTimers()
  }
})

test('typing again restarts the delay instead of showing intermediate errors', async () => {
  vi.useFakeTimers()
  try {
    const editor = mountEditor()

    editor.text.value = 'A +'
    await nextTick()
    vi.advanceTimersByTime(1000)
    editor.text.value = 'A + B'
    await nextTick()
    vi.advanceTimersByTime(1500)
    expect(editor.errors.value).toEqual([])
  } finally {
    vi.useRealTimers()
  }
})

test('commit shows the error immediately and keeps it despite a pending delay', async () => {
  vi.useFakeTimers()
  try {
    const editor = mountEditor()

    editor.text.value = 'A +'
    await nextTick()
    expect(editor.errors.value).toEqual([])

    expect('errors' in editor.commit()).toBe(true)
    expect(editor.errors.value).toEqual([
      'Invalid formula: The formula ends unexpectedly; add a metric id (e.g. A) or a number.'
    ])

    vi.advanceTimersByTime(1500)
    expect(editor.errors.value).toEqual([
      'Invalid formula: The formula ends unexpectedly; add a metric id (e.g. A) or a number.'
    ])
  } finally {
    vi.useRealTimers()
  }
})

test('a commit error is not wiped by a validation pending from earlier input', async () => {
  vi.useFakeTimers()
  try {
    const editor = mountEditor()
    const emptyError = ['The formula is empty; add a metric id (e.g. A) or a number.']

    editor.text.value = 'A +'
    await nextTick()
    editor.text.value = ''
    await nextTick()

    expect('errors' in editor.commit()).toBe(true)
    expect(editor.errors.value).toEqual(emptyError)

    vi.advanceTimersByTime(1500)
    expect(editor.errors.value).toEqual(emptyError)
  } finally {
    vi.useRealTimers()
  }
})
