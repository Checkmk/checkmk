/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeAll, describe, expect, jest, test } from '@jest/globals'

import { init_click_action_dispatcher } from '@/modules/click_action_dispatcher'
import '@/modules/click_actions'

// The actions persist state via AJAX, which jsdom can't serve
jest.mock('@/modules/ajax', () => ({ call_ajax: jest.fn() }))
// Imported via the page menu, but loads d3, which jest can't import
jest.mock('@/modules/valuespecs', () => ({}))

function click(html: string, selector: string): MouseEvent {
  document.body.innerHTML = html
  const event = new MouseEvent('click', { bubbles: true, cancelable: true })
  document.querySelector(selector)!.dispatchEvent(event)
  return event
}

describe('click actions', () => {
  beforeAll(() => {
    init_click_action_dispatcher()
  })

  test('links in the header of a foldable container are followed', () => {
    const event = click(
      '<div><div data-cmk_on_click="foldable_container_toggle"' +
        ' data-cmk_on_click_arguments=\'{"treename": "t", "id": "i", "fetch_url": "",' +
        ' "save_state": "false"}\'><a href="view.py">link</a></div>' +
        '<ul id="tree.t.i" class="closed"></ul></div>',
      'a'
    )

    expect(event.defaultPrevented).toBe(false)
  })
})
