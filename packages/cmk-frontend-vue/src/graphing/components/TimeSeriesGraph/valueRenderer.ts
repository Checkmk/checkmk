/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type UnitFormat, userSpecificUnit } from 'cmk-ui-library/lib/unit-format/unitFormatter'

export type ValueRenderer = (value: number) => string

/**
 * Renders values of `unit` shown next to a graph whose axis resolves `valueResolution`: precise
 * enough to tell two values that far apart from each other, whatever prefix each value ends up
 * with. Without an axis (`null`) the unit's own precision applies.
 */
export function valueRenderer(unit: UnitFormat, valueResolution: number | null): ValueRenderer {
  const { formatter } = userSpecificUnit(unit, 'celsius')
  return (value) => formatter.render(value, valueResolution)
}
