/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeAll, beforeEach, describe, expect, test } from '@jest/globals'

import { init_enter_submit_dispatcher } from '@/modules/enter_submit'

function pressKey(input: HTMLInputElement, key: string): KeyboardEvent {
  const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true })
  input.dispatchEvent(event)
  return event
}

describe('init_enter_submit_dispatcher', () => {
  let clicks: number

  beforeAll(() => {
    init_enter_submit_dispatcher()
  })

  beforeEach(() => {
    document.body.innerHTML =
      '<input id="with_submit" data-cmk_enter_submit="the_button">' +
      '<input id="without_submit">' +
      '<button id="the_button"></button>'
    clicks = 0
    document.getElementById('the_button')!.addEventListener('click', () => clicks++)
  })

  test('Enter clicks the button the input names', () => {
    const input = document.getElementById('with_submit') as HTMLInputElement

    const event = pressKey(input, 'Enter')

    expect([clicks, event.defaultPrevented]).toEqual([1, true])
  })

  test('other keys are typed into the input', () => {
    const input = document.getElementById('with_submit') as HTMLInputElement

    const event = pressKey(input, 'a')

    expect([clicks, event.defaultPrevented]).toEqual([0, false])
  })

  test('Enter in an input without a submit button keeps its default', () => {
    const input = document.getElementById('without_submit') as HTMLInputElement

    const event = pressKey(input, 'Enter')

    expect([clicks, event.defaultPrevented]).toEqual([0, false])
  })
})
