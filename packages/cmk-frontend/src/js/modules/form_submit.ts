/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// Call the handler when the form is really submitted. The listener is registered on the document,
// so it runs after the form's own submit handlers, which may cancel the submit, e.g. the live
// search of the network visualization.
export function on_uncancelled_submit(form: HTMLElement, handler: () => void) {
  document.addEventListener('submit', (event: Event) => {
    if (event.target === form && !event.defaultPrevented) handler()
  })
}
