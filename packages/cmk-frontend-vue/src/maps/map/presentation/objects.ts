/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MapElement } from '@/maps/types/api'
import { newMapElement } from '@/maps/utils/model'

import { type BindableElement, hasBinding } from './binding'

/**
 * Expose a bound presentation element as a transient MapElement so the
 * shared view-mode surfaces (HoverMenu, DetailDrawer) work on presentation
 * maps without knowing about the element model. The id matches the
 * element's id, which is also the key of its entry in the states store.
 */
export function mapElementFromElement(el: BindableElement): MapElement | null {
  if (!hasBinding(el)) {
    return null
  }
  const type: MapElement['type'] = el.aggregation_id
    ? 'aggregation'
    : el.group_name
      ? el.object_type === 'servicegroup'
        ? 'servicegroup'
        : 'hostgroup'
      : el.service_description
        ? 'service'
        : 'host'
  return newMapElement({
    id: el.id,
    type,
    host_name: el.host_name ?? null,
    service_description: el.service_description ?? null,
    group_name: el.group_name ?? null,
    aggregation_id: el.aggregation_id ?? null,
    connection_id: el.connection_id ?? null,
    only_hard_states: el.only_hard_states ?? false
  })
}
