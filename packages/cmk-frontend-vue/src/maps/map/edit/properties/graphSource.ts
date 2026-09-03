/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { ObjectForm } from '@/maps/map/edit/properties/objectForm'
import type { MapElement } from '@/maps/types/api'

/** Where a graph object's curves come from. */
export type GraphSource = 'auto' | 'metrics' | 'template'

/**
 * Which source an object is on, read back from what it stored: a template id
 * wins, then a hand-picked metric list, otherwise the graph follows whatever
 * the bound service measures.
 */
export function graphSourceOf(object: MapElement): GraphSource {
  if (object.graph_id) {
    return 'template'
  }
  if (object.graph_metric?.length) {
    return 'metrics'
  }
  return 'auto'
}

/**
 * Switching the source drops what the other ones stored — a leftover template
 * id would keep winning over the metric list the operator just picked.
 */
export function applyGraphSource(form: ObjectForm, source: GraphSource): void {
  if (source !== 'template') {
    form.graph_id = null
  }
  if (source !== 'metrics') {
    form.graph_metric = []
  }
}

/** The time spans a graph object can be drawn over. */
export function graphTimeWindows(): { minutes: number; title: TranslatedString }[] {
  return [
    { minutes: 60, title: untranslated('1 h') },
    { minutes: 240, title: untranslated('4 h') },
    { minutes: 720, title: untranslated('12 h') },
    { minutes: 1440, title: untranslated('24 h') },
    { minutes: 10080, title: untranslated('7 d') }
  ]
}
