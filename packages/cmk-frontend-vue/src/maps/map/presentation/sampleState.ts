/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Design-first placeholders: an unbound data slot previews with plausible
// sample data in the editor, so a slide can be fully designed before any
// monitoring object is attached. Everything derives deterministically from the
// element id, so previews are stable across renders and saves.
import type { ObjectState, PresentationElement } from '@/maps/types/api'
import { newObjectState } from '@/maps/utils/model'

import { isBindable } from './binding'

function hash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) >>> 0
  }
  return h
}

// Mostly healthy with the occasional WARNING — a believable wall, not a crisis.
const SAMPLE_STATES = ['OK', 'OK', 'OK', 'WARNING', 'OK', 'OK'] as const

export function sampleStateFor(el: PresentationElement): ObjectState {
  const h = hash(el.id)
  const state = SAMPLE_STATES[h % SAMPLE_STATES.length] ?? 'OK'
  const value = 25 + (h % 60)
  const metric =
    (isBindable(el) &&
      (el.kind === 'data' ? el.display.gadget_metric : (el.flow_metric ?? null))) ||
    'util'
  return newObjectState({
    object_id: el.id,
    type: 'service',
    state,
    output: 'Sample data',
    perf_data: `${metric}=${value}%;80;90;0;100`
  })
}
