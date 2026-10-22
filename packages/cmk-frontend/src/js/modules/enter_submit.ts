/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Delegated Enter key handling of text inputs
 *
 * An enforcing Content Security Policy forbids inline event handlers like
 * `onkeydown="..."`. Instead, a text input names the ID of the button to click
 * on Enter in its `data-cmk_enter_submit` attribute (see the `submit` argument
 * of cmk.gui.htmllib.html:HTMLGenerator.text_input). This is independent of
 * the TS function an input may call, so both can be used together.
 */
export function init_enter_submit_dispatcher() {
  document.addEventListener('keydown', (event: KeyboardEvent) => {
    if (event.key !== 'Enter' || !(event.target instanceof HTMLElement)) return
    const submit = event.target.dataset.cmk_enter_submit
    if (submit === undefined) return
    document.getElementById(submit)?.click()
    event.preventDefault()
    event.stopPropagation()
  })
}
