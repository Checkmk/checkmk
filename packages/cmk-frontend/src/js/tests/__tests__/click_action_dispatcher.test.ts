/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeAll, describe, expect, test } from '@jest/globals'

import {
  init_click_action_dispatcher,
  prevent_hash_link_navigation,
  register_click_actions
} from '@/modules/click_action_dispatcher'

const received_events: (MouseEvent | undefined)[] = []

function click(html: string): MouseEvent {
  document.body.innerHTML = html
  const event = new MouseEvent('click', { bubbles: true, cancelable: true })
  document.querySelector('a')!.dispatchEvent(event)
  return event
}

describe('click action dispatcher', () => {
  beforeAll(() => {
    // Real names, as only known click actions can be registered. The test only loads the
    // dispatcher, so these implementations are the only ones.
    register_click_actions({
      reload_page: () => true,
      add_bookmark: (_element, _options, event) => {
        received_events.push(event)
      }
    })
    init_click_action_dispatcher()
  })

  test('hands the click event to the action', () => {
    document.body.innerHTML = '<a href="#" data-cmk_on_click="add_bookmark"><span>link</span></a>'
    const click = new MouseEvent('click', { bubbles: true, cancelable: true, ctrlKey: true })

    document.querySelector('span')!.dispatchEvent(click)

    expect(received_events).toEqual([click])
  })

  test('keeps the default action if the action returns true', () => {
    const event = click('<a href="view.py" data-cmk_on_click="reload_page">link</a>')

    expect(event.defaultPrevented).toBe(false)
  })

  test('prevents the default action if the action returns nothing', () => {
    const event = click('<a href="view.py" data-cmk_on_click="add_bookmark">link</a>')

    expect(event.defaultPrevented).toBe(true)
  })

  test('prevents the default action if the arguments are malformed', () => {
    const errors: unknown[] = []
    // Like a browser, jsdom reports exceptions of event listeners as uncaught errors
    const on_error = (error_event: ErrorEvent) => {
      errors.push(error_event.error)
      error_event.preventDefault()
    }
    window.addEventListener('error', on_error)
    let event: MouseEvent
    try {
      event = click(
        '<a href="view.py" data-cmk_on_click="reload_page" data-cmk_on_click_arguments="{">x</a>'
      )
    } finally {
      window.removeEventListener('error', on_error)
    }

    expect(errors).toEqual([expect.any(SyntaxError)])
    expect(event.defaultPrevented).toBe(true)
  })
})

describe('hash link guard', () => {
  beforeAll(() => {
    prevent_hash_link_navigation()
  })

  test('links to "#" are not followed', () => {
    document.body.innerHTML = '<a href="#"><span>link</span></a>'
    const event = new MouseEvent('click', { bubbles: true, cancelable: true })

    document.querySelector('span')!.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
  })
})
