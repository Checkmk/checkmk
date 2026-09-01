/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import { useCalculationEditor } from '@/graphing/designer/calculation/composables/useCalculationEditor'
import { DEFAULT_TITLE_MACRO, type GraphItem } from '@/graphing/designer/types'

import { formulaItem, rrdMetricItem, rrdQueryItem } from '../../fixtures'

const NEXT_ID = 'X'
const NEXT_COLOR = '#ffd703'

function mountEditor(
  initial: GraphItem[] = [rrdMetricItem('A'), rrdMetricItem('B')],
  nextColor: () => string = () => NEXT_COLOR
) {
  const items = ref<GraphItem[]>(initial)
  let api!: ReturnType<typeof useCalculationEditor>
  render(
    defineComponent({
      setup() {
        api = useCalculationEditor(
          () => items.value,
          'rrd',
          () => NEXT_ID,
          nextColor
        )
        return () => null
      }
    })
  )
  return { editor: api, items }
}

test('commits an add with the entered title and formula', () => {
  const { editor } = mountEditor()
  editor.formula.text.value = 'A + B'
  editor.title.value = 'My calculation'
  const result = editor.commit()
  expect(result).toMatchObject({
    kind: 'add',
    draft: {
      type: 'rrd_formula',
      title: 'My calculation',
      color: NEXT_COLOR,
      ast: {
        op: 'sum',
        operands: [
          { op: 'ref', id: 'A' },
          { op: 'ref', id: 'B' }
        ]
      }
    },
    refVisibility: null
  })
})

test('the color follows the changing default until one is picked, and resets on commit', () => {
  const fallback = ref('#111111')
  const { editor } = mountEditor(undefined, () => fallback.value)
  expect(editor.color.value).toBe('#111111')
  fallback.value = '#222222'
  expect(editor.color.value).toBe('#222222')

  editor.color.value = '#123456'
  fallback.value = '#333333'
  expect(editor.color.value).toBe('#123456')

  editor.formula.text.value = 'A'
  const result = editor.commit()
  expect('kind' in result && result.draft.color).toBe('#123456')
  expect(editor.color.value).toBe('#333333')
})

test('falls back to the title macro when the title is cleared', () => {
  const { editor } = mountEditor()
  editor.formula.text.value = 'A'
  editor.title.value = '   '
  const result = editor.commit()
  expect('kind' in result && result.draft.title).toBe(DEFAULT_TITLE_MACRO)
})

test('committing an empty formula fails with a message', () => {
  const { editor } = mountEditor()
  const result = editor.commit()
  expect('errors' in result && result.errors.length).toBeGreaterThan(0)
})

test('returns the active editor errors and leaves the form intact on failure', () => {
  const { editor } = mountEditor()
  editor.formula.text.value = 'A +'
  const result = editor.commit()
  expect('errors' in result).toBe(true)
  expect(editor.formula.text.value).toBe('A +')
})

test('the checked hide box hides the direct refs; unchecked changes nothing when adding', () => {
  const { editor } = mountEditor()
  editor.formula.text.value = 'A + B'
  editor.hideSourceMetrics.value = true
  const hidden = editor.commit()
  expect('kind' in hidden && hidden.refVisibility).toEqual({ ids: ['A', 'B'], visible: false })

  expect(editor.hideSourceMetrics.value).toBe(true)
  editor.hideSourceMetrics.value = false
  editor.formula.text.value = 'A'
  const unchanged = editor.commit()
  expect('kind' in unchanged && unchanged.refVisibility).toBeNull()
})

test('switching the mode clears the form and cancels an active edit', () => {
  const target = formulaItem('D', { ast: { op: 'ref', id: 'A' } })
  const { editor } = mountEditor([rrdMetricItem('A'), target])
  editor.startEdit(target)
  expect(editor.editingId.value).toBe('D')
  editor.switchMode('transformation')
  expect(editor.editingId.value).toBeNull()
  expect(editor.formula.text.value).toBe('')
  expect(editor.title.value).toBe('')
  expect(editor.color.value).toBe(NEXT_COLOR)
})

test('startEdit seeds the operations editor from a plain formula', () => {
  const target = formulaItem('D', {
    title: 'Difference',
    ast: {
      op: 'difference',
      operands: [
        { op: 'ref', id: 'A' },
        { op: 'ref', id: 'B' }
      ]
    }
  })
  const { editor } = mountEditor([rrdMetricItem('A'), rrdMetricItem('B'), target])
  editor.startEdit(target)
  expect(editor.mode.value).toBe('operations')
  expect(editor.formula.text.value).toBe('A - B')
  expect(editor.title.value).toBe('Difference')
})

test('startEdit seeds the item color and shows a default title as empty', () => {
  const target = formulaItem('D', {
    title: DEFAULT_TITLE_MACRO,
    color: '#ec48b6',
    ast: { op: 'ref', id: 'A' }
  })
  const { editor } = mountEditor([rrdMetricItem('A'), target])
  editor.startEdit(target)
  expect(editor.title.value).toBe('')
  expect(editor.color.value).toBe('#ec48b6')

  const result = editor.commit()
  expect('kind' in result && result.draft).toMatchObject({
    title: DEFAULT_TITLE_MACRO,
    color: '#ec48b6'
  })
})

test('startEdit seeds the transformation editor from a percentile', () => {
  const target = formulaItem('D', {
    ast: { op: 'percentile', percentile: 90, operand: { op: 'ref', id: 'A' } }
  })
  const { editor } = mountEditor([rrdMetricItem('A'), target])
  editor.startEdit(target)
  expect(editor.mode.value).toBe('transformation')
  expect(editor.transformation.selectedId.value).toBe('A')
  expect(editor.transformation.percentile.value).toBe('90')
})

test('startEdit derives the tri-state hide box from the refs', () => {
  const target = formulaItem('D', {
    ast: {
      op: 'sum',
      operands: [
        { op: 'ref', id: 'A' },
        { op: 'ref', id: 'B' }
      ]
    }
  })

  const allVisible = mountEditor([rrdMetricItem('A'), rrdMetricItem('B'), target])
  allVisible.editor.startEdit(target)
  expect(allVisible.editor.hideSourceMetrics.value).toBe(false)

  const allHidden = mountEditor([
    rrdMetricItem('A', { visible: false }),
    rrdMetricItem('B', { visible: false }),
    target
  ])
  allHidden.editor.startEdit(target)
  expect(allHidden.editor.hideSourceMetrics.value).toBe(true)

  const mixed = mountEditor([rrdMetricItem('A', { visible: false }), rrdMetricItem('B'), target])
  mixed.editor.startEdit(target)
  expect(mixed.editor.hideSourceMetrics.value).toBe('indeterminate')
})

test('committing an edit emits an update, restores visibility when unchecked', () => {
  const target = formulaItem('D', { ast: { op: 'ref', id: 'A' } })
  const { editor } = mountEditor([rrdMetricItem('A', { visible: false }), target])
  editor.startEdit(target)
  expect(editor.hideSourceMetrics.value).toBe(true)
  editor.hideSourceMetrics.value = false
  const result = editor.commit()
  expect(result).toMatchObject({
    kind: 'update',
    id: 'D',
    refVisibility: { ids: ['A'], visible: true }
  })
  expect(editor.editingId.value).toBeNull()
})

test('an indeterminate hide box leaves visibility unchanged on update', () => {
  const target = formulaItem('D', {
    ast: {
      op: 'sum',
      operands: [
        { op: 'ref', id: 'A' },
        { op: 'ref', id: 'B' }
      ]
    }
  })
  const { editor } = mountEditor([
    rrdMetricItem('A', { visible: false }),
    rrdMetricItem('B'),
    target
  ])
  editor.startEdit(target)
  expect(editor.hideSourceMetrics.value).toBe('indeterminate')
  const result = editor.commit()
  expect('kind' in result && result.refVisibility).toBeNull()
})

test('insertRef feeds the active editor', () => {
  const { editor } = mountEditor()
  editor.insertRef('A')
  expect(editor.formula.text.value).toBe('A')
  editor.switchMode('transformation')
  editor.insertRef('B')
  expect(editor.transformation.selectedId.value).toBe('B')
})

test('explains why a dynamic row blocks in transformation mode and why cycle rows block on edit', () => {
  const query = rrdQueryItem('C')
  const target = formulaItem('D', { ast: { op: 'ref', id: 'A' } })
  const dependent = formulaItem('F', { ast: { op: 'ref', id: 'D' } })
  const metric = rrdMetricItem('A')
  const { editor } = mountEditor([metric, query, target, dependent])

  expect(editor.itemBlockReason(query)).toBeNull()
  editor.switchMode('transformation')
  expect(editor.itemBlockReason(query)).toBe(
    'A percentile needs one metric. This query selects several. Aggregate it in a calculation first.'
  )
  editor.switchMode('operations')

  editor.startEdit(target)
  expect(editor.itemBlockReason(target)).toBe('This calculation is currently being edited.')
  expect(editor.itemBlockReason(dependent)).toBe(
    'This calculation refers to the one being edited. A reference back would create a cycle.'
  )
  expect(editor.itemBlockReason(metric)).toBeNull()
})

test('shows an added alert with the id the store will assign, an updated alert on edit', () => {
  const { editor, items } = mountEditor()
  editor.formula.text.value = 'A'
  const result = editor.commit()
  expect('kind' in result && result.kind).toBe('add')
  expect(editor.successAlert.value).toMatchObject({ id: NEXT_ID, kind: 'added' })

  editor.dismissAlert()
  expect(editor.successAlert.value).toBeNull()

  const added = formulaItem(NEXT_ID, { ast: { op: 'ref', id: 'A' } })
  items.value = [...items.value, added]
  editor.startEdit(added)
  const update = editor.commit()
  expect('kind' in update && update.kind).toBe('update')
  expect(editor.successAlert.value).toMatchObject({ id: NEXT_ID, kind: 'updated' })
})
