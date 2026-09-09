/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type ValidationIssue,
  collectDirectRefs,
  referencesTransitively,
  validateFormula
} from '@/graphing/designer/calculation/formula'
import type { Domain, GraphItem } from '@/graphing/designer/types'

import { formulaItem, items, parseOrThrow } from '../../fixtures'

function check(
  source: string,
  domain: Domain = 'rrd',
  editedItemId: string | null = null,
  against: GraphItem[] = items
): ValidationIssue[] {
  return validateFormula(parseOrThrow(source), against, domain, editedItemId)
}

test('accepts a valid RRD formula', () => {
  expect(check('A + B')).toEqual([])
})

test('accepts a valid OpenTelemetry metrics formula in the metric_backend domain', () => {
  expect(check('E + 1', 'metric_backend')).toEqual([])
})

test('flags an unknown reference (E2)', () => {
  expect(check('A + Z')).toEqual([{ code: 'unknown-ref', id: 'Z' }])
})

test('flags mixing RRD with metric backend (E3)', () => {
  expect(check('A + E')).toEqual([{ code: 'domain-mismatch', id: 'E' }])
})

test('requires consolidation for a bare dynamic query (E5)', () => {
  expect(check('C')).toEqual([{ code: 'needs-consolidation', id: 'C' }])
  expect(check('C + B')).toEqual([{ code: 'needs-consolidation', id: 'C' }])
})

test('accepts a dynamic query wrapped as the sole argument of a function', () => {
  expect(check('avg(C)')).toEqual([])
  expect(check('sum(C)')).toEqual([])
  expect(check('min(C) - max(C)')).toEqual([])
})

test('rejects a dynamic query that is not the sole argument', () => {
  expect(check('avg(C, B)')).toEqual([{ code: 'needs-consolidation', id: 'C' }])
  expect(check('avg(C + B)')).toEqual([{ code: 'needs-consolidation', id: 'C' }])
})

test('deduplicates repeated issues', () => {
  expect(check('C + C')).toEqual([{ code: 'needs-consolidation', id: 'C' }])
})

test('flags a formula referencing the item being edited', () => {
  expect(check('D + 1', 'rrd', 'D')).toEqual([{ code: 'self-ref', id: 'D' }])
})

test('flags a reference cycle through another formula', () => {
  const withF = [...items, formulaItem('F', { ast: { op: 'ref', id: 'D' } })]
  expect(check('F + 1', 'rrd', 'D', withF)).toEqual([{ code: 'cyclic-ref', id: 'F' }])
})

test('flags a cycle across several formulas and percentile operands', () => {
  const chain = [
    ...items,
    formulaItem('F', { ast: { op: 'ref', id: 'D' } }),
    formulaItem('G', { ast: { op: 'percentile', percentile: 95, operand: { op: 'ref', id: 'F' } } })
  ]
  expect(check('G + 1', 'rrd', 'D', chain)).toEqual([{ code: 'cyclic-ref', id: 'G' }])
})

test('collects direct refs uniquely, in first appearance order', () => {
  expect(collectDirectRefs(parseOrThrow('B + A * B'))).toEqual(['B', 'A'])
  expect(
    collectDirectRefs({ op: 'percentile', percentile: 95, operand: { op: 'ref', id: 'A' } })
  ).toEqual(['A'])
})

test('detects transitive references through formula items', () => {
  const withF = [...items, formulaItem('F', { ast: { op: 'ref', id: 'D' } })]
  const byId = new Map(withF.map((item) => [item.id, item]))
  expect(referencesTransitively(byId, 'F', 'A')).toBe(true)
  expect(referencesTransitively(byId, 'F', 'B')).toBe(false)
})
