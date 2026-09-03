/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  applyGraphSource,
  graphSourceOf,
  graphTimeWindows
} from '@/maps/map/edit/properties/graphSource'
import { formFromObject } from '@/maps/map/edit/properties/objectForm'
import type { MapElement } from '@/maps/types/api'

import { anObject } from '../../../support/fixtures'

function aGraph(extra: Partial<MapElement>): MapElement {
  return anObject({ id: 'g', type: 'graph', ...extra })
}

describe('graphSourceOf', () => {
  it('lets a stored template win over a metric list', () => {
    expect(graphSourceOf(aGraph({ graph_id: 'tpl', graph_metric: ['load1'] }))).toBe('template')
  })

  it('reads a metric list as the hand-picked source', () => {
    expect(graphSourceOf(aGraph({ graph_metric: ['load1'] }))).toBe('metrics')
  })

  it('falls back to following the bound service', () => {
    expect(graphSourceOf(aGraph({}))).toBe('auto')
    expect(graphSourceOf(aGraph({ graph_metric: [] }))).toBe('auto')
  })
})

describe('applyGraphSource', () => {
  it('drops what the other sources stored', () => {
    const form = formFromObject(aGraph({ graph_id: 'tpl', graph_metric: ['load1'] }), { z: 1 })

    applyGraphSource(form, 'metrics')
    expect(form.graph_id).toBeNull()
    expect(form.graph_metric).toEqual(['load1'])

    applyGraphSource(form, 'template')
    expect(form.graph_metric).toEqual([])

    applyGraphSource(form, 'auto')
    expect(form.graph_id).toBeNull()
    expect(form.graph_metric).toEqual([])
  })
})

describe('graphTimeWindows', () => {
  it('offers the spans in minutes, shortest first', () => {
    expect(graphTimeWindows().map((window) => window.minutes)).toEqual([60, 240, 720, 1440, 10080])
  })
})
