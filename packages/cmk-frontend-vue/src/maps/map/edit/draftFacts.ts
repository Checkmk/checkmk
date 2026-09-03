/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { NewObjectDraft } from '@/maps/map/composables/useMapEditor'
import type { TranslateFn } from '@/maps/utils/dropdownOptions'

/**
 * Whether the draft object names something the map can show yet: a host needs a
 * hostname, a service needs both, a line or a textbox needs nothing at all.
 * Objects that carry only geometry are placeable the moment their type is
 * picked.
 */
export function isDraftPlaceable(draft: NewObjectDraft): boolean {
  switch (draft.type) {
    case 'host':
      return !!draft.host_name
    case 'service':
      return !!draft.host_name && !!draft.service_description
    case 'hostgroup':
    case 'servicegroup':
      return !!draft.group_name
    case 'dyngroup':
      return !!draft.object_filter.trim()
    case 'map':
      return !!draft.map_name
    case 'aggregation':
      return !!draft.aggregation_id
    case 'image':
      return !!draft.image_src
    case 'line':
    case 'textbox':
    case 'graph':
      return true
    default:
      return false
  }
}

/**
 * Clears every binding a draft carries, keeping only its type. Switching the
 * type re-uses the same draft object, and a hostname left over from the
 * previous type would silently end up on the new object.
 */
export function clearDraftBindings(draft: NewObjectDraft): void {
  draft.host_name = ''
  draft.service_description = ''
  draft.group_name = ''
  draft.map_name = ''
  draft.aggregation_id = ''
  draft.expand_depth = 0
  draft.label_text = ''
  draft.image_src = ''
  draft.graph_url = ''
}

/** How densely the canvas snaps while placing. Offered by the panel and the
 *  grid FAB alike, so the sizes are named once. */
export function snapGridSizes(_t: TranslateFn): { value: number; title: TranslatedString }[] {
  return [
    { value: 0, title: _t('Off') },
    { value: 10, title: untranslated('10 px') },
    { value: 20, title: untranslated('20 px') },
    { value: 50, title: untranslated('50 px') }
  ]
}
