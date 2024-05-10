/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import * as d3 from 'd3'

export function clicked_checkbox_label(target: HTMLLabelElement) {
  // TODO: Better use the <label for="id"> mechanic instead of this workaround
  const parent_node = target.parentNode
  if (parent_node == null) {
    return
  }
  const bound_input_field = d3
    .select(parent_node as HTMLSpanElement)
    .select<HTMLInputElement>('input')

  if (bound_input_field.empty()) {
    return
  }
  bound_input_field.node()!.click()
}
