/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Whether a `focusout` event means focus genuinely left `event.currentTarget` (rather than just
 * hopping between its own descendants). Two cases count as *not* leaving:
 *  - the new focus target (`relatedTarget`) is a descendant of the element, and
 *  - a blur with no `relatedTarget` while the whole window lost focus (a tab/window switch), so an
 *    edit survives switching away and back.
 *
 * Bind to a `focusout` handler and act only when this returns `true`.
 */
export function focusLeftElement(event: FocusEvent): boolean {
  const next = event.relatedTarget
  const current = event.currentTarget
  // Focus only hopping between the element's own descendants is not leaving.
  if (next instanceof Node && current instanceof HTMLElement && current.contains(next)) {
    return false
  }
  // A blur with no relatedTarget while the whole window lost focus is a tab/window switch, not a
  // leave.
  return !(next === null && !document.hasFocus())
}
