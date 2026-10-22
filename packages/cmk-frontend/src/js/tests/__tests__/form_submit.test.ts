/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from '@jest/globals'

import { on_uncancelled_submit } from '@/modules/form_submit'

function submit(cancel: boolean): number {
  document.body.innerHTML = '<form></form>'
  const form = document.querySelector('form')!
  let calls = 0
  on_uncancelled_submit(form, () => calls++)
  if (cancel) {
    form.addEventListener('submit', (event) => event.preventDefault())
  }

  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))

  return calls
}

describe('on_uncancelled_submit', () => {
  test('calls the handler when the form is submitted', () => {
    expect(submit(false)).toBe(1)
  })

  test('skips the handler when a later handler of the form cancels the submit', () => {
    expect(submit(true)).toBe(0)
  })
})
