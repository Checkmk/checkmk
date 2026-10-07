/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeAll, describe, expect, test } from '@jest/globals'

import { prevent_hash_link_navigation } from '@/modules/click_action_dispatcher'

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
