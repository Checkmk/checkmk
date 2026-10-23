/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/** Whether the browser marks a focus as the keyboard's, as it does for `:focus-visible`. */
export function byKeyboard(event: FocusEvent): boolean {
  return event.target instanceof Element && event.target.matches(':focus-visible')
}
