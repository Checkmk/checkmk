/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Shared derivations for a map's visuals ownership + sharing state, used by
// the overview table, the cards and the own/other/built-in grouping. Returns
// semantic kinds (not translated strings) so each component owns its i18n.
import type { MapRead } from '@/maps/types/api'

export type MapVisibility = 'private' | 'published' | 'shared_groups' | 'shared_sites'
export type MapOwnerKind = 'builtin' | 'you' | 'other'

export function mapVisibility(map: MapRead): MapVisibility {
  const p = map.public
  if (p === true) {
    return 'published'
  }
  if (Array.isArray(p)) {
    return p[0] === 'sites' ? 'shared_sites' : 'shared_groups'
  }
  return 'private'
}

export function mapOwnerKind(map: MapRead, currentUserId: string | undefined): MapOwnerKind {
  if (map.is_builtin) {
    return 'builtin'
  }
  if (map.owner && map.owner === currentUserId) {
    return 'you'
  }
  return 'other'
}
