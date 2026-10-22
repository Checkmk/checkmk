/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from '@jest/globals'

import { listof_entry_index } from '@/modules/valuespec_listof'

function button(id: string): HTMLElement {
  return document.getElementById(id)!
}

describe('listof_entry_index', () => {
  document.body.innerHTML = `
    <table><tbody id="vp_container">
      <tr id="vp_entry_3"><td>
        <a id="outer_delete"></a>
        <table><tbody id="vp_3_inner_container">
          <tr id="vp_3_inner_entry_2"><td><a id="inner_delete"></a></td></tr>
        </tbody></table>
      </td></tr>
    </tbody></table>
    <a id="outside"></a>`

  test('finds the entry containing the element', () => {
    expect(listof_entry_index(button('outer_delete'), 'vp')).toBe('3')
  })

  test('finds the entry of a nested list', () => {
    expect(listof_entry_index(button('inner_delete'), 'vp_3_inner')).toBe('2')
  })

  test('finds the entry of the outer list from within a nested list', () => {
    expect(listof_entry_index(button('inner_delete'), 'vp')).toBe('3')
  })

  test('fails for an element outside of the entries', () => {
    expect(() => listof_entry_index(button('outside'), 'vp')).toThrow()
  })
})
