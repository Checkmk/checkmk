/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, test } from '@jest/globals'

import { makeLoadingTransition } from '@/modules/utils'

function clickLink(linkTarget: string | null, init: MouseEventInit = {}): HTMLElement {
  document.body.innerHTML = '<div id="content_area"><a href="#"><span>link</span></a></div>'
  const link = document.querySelector('a')!
  if (linkTarget !== null) {
    link.target = linkTarget
  }
  link.addEventListener('click', (event) => {
    event.preventDefault()
    makeLoadingTransition(null, 0, undefined, event)
  })
  document
    .querySelector('span')!
    .dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, ...init }))
  return document.getElementById('content_area')!
}

describe('makeLoadingTransition', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  test.each([
    ['a plain click', null, {}],
    ['a link targeting _self', '_self', {}]
  ])('prepares the transition for %s', (_name, linkTarget, init) => {
    expect(clickLink(linkTarget, init).hasAttribute('data-prepare-loading-transition')).toBe(true)
  })

  test.each([
    ['a ctrl click', null, { ctrlKey: true }],
    ['a meta click', null, { metaKey: true }],
    ['a shift click', null, { shiftKey: true }],
    ['a middle click', null, { button: 1 }],
    ['a link targeting _blank', '_blank', {}]
  ])('skips the transition for %s', (_name, linkTarget, init) => {
    expect(clickLink(linkTarget, init).hasAttribute('data-prepare-loading-transition')).toBe(false)
  })
})
