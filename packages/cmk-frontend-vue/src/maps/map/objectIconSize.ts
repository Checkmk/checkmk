/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MapElement } from '@/maps/types/api'
import { GADGET_DEFAULT_SIZE } from '@/maps/utils/gadget'

/**
 * How large an object's icon renders, in map units.
 *
 * The object's own size wins; a gadget then has its own default, because an
 * instrument needs more room to be readable than an icon does; otherwise the
 * map's setting applies, and finally the site's. Both the placement and the
 * line endpoints bound to an object read this, so they agree on where the
 * object's edge is.
 */
export function objectIconSize(
  object: MapElement,
  sizes: { map: number | null | undefined; override: number | undefined; fallback: number }
): number {
  if (object.display?.image_size !== null && object.display?.image_size !== undefined) {
    return object.display.image_size
  }
  if (object.display?.mode === 'gadget') {
    return GADGET_DEFAULT_SIZE
  }
  return sizes.override ?? sizes.map ?? sizes.fallback
}
