/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, jest, test } from '@jest/globals'

import { call_ajax } from '@/modules/ajax'
import { fetch_hot_menu_entries } from '@/modules/page_menu'

jest.mock('@/modules/ajax', () => ({ call_ajax: jest.fn() }))
// Imported via the forms, but loads d3, which jest can't import
jest.mock('@/modules/valuespecs', () => ({}))

function start_fetch() {
  document.body.innerHTML = '<a id="menu_entry_bake"></a><div id="message"></div>'
  fetch_hot_menu_entries('ajax_hot_state.py', ['bake'], 'message')
  return jest.mocked(call_ajax).mock.lastCall![1]!
}

function fetch_with_response(response: object) {
  start_fetch().response_handler!(null, JSON.stringify(response))
}

function fetch_with_http_error(status: number) {
  start_fetch().error_handler!(null, status, 'Bad Gateway')
}

function entry_is_hot(): boolean {
  return document.getElementById('menu_entry_bake')!.classList.contains('hot')
}

describe('fetch_hot_menu_entries', () => {
  test('a failed request marks the entries hot', () => {
    fetch_with_response({ result_code: 1, result: 'Error running automation call' })

    expect(entry_is_hot()).toBe(true)
  })

  test('an HTTP error marks the entries hot', () => {
    fetch_with_http_error(502)

    expect(entry_is_hot()).toBe(true)
  })

  test('an aborted request leaves the entries unhighlighted', () => {
    fetch_with_http_error(0)

    expect(entry_is_hot()).toBe(false)
  })

  test('a response without pending bakes leaves the entries unhighlighted', () => {
    fetch_with_response({ result_code: 0, result: { hot: false, message: null } })

    expect(entry_is_hot()).toBe(false)
  })

  test('the message of the response is shown', () => {
    fetch_with_response({
      result_code: 0,
      result: { hot: true, message: '<div class="warning">Building fails</div>' }
    })

    expect(document.getElementById('message')!.textContent).toBe('Building fails')
  })
})
