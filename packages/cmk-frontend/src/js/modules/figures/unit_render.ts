/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { SIUnitPrefixes, fmt_nic_speed, fmt_number_with_precision } from '@/modules/number_format'

// Value renderers the server selects by name, so that no JavaScript code has
// to be sent along with the figure data and compiled in the browser.
export interface NamedUnitRender {
  name: 'nic_speed'
  factor: number
}

type UnitRenderFunction = (v: number) => string

const NAMED_UNIT_RENDERERS: Record<
  NamedUnitRender['name'],
  (render: NamedUnitRender) => UnitRenderFunction
> = {
  // fmt_nic_speed parses its argument: hand over the same string the implicit
  // number to string conversion of former code produced.
  nic_speed: (render) => (v) => fmt_nic_speed(String(v * render.factor))
}

export function unit_render_function(render?: NamedUnitRender): UnitRenderFunction {
  if (
    render !== undefined &&
    Object.prototype.hasOwnProperty.call(NAMED_UNIT_RENDERERS, render.name)
  ) {
    return NAMED_UNIT_RENDERERS[render.name](render)
  }
  return (v) => fmt_number_with_precision(v, SIUnitPrefixes, 2, true)
}
