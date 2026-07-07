/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ModeHostSite } from 'cmk-shared-typing/typescript/mode_host'

import { resolveSiteId } from '@/mode-host/lib/site'

const sites: Array<ModeHostSite> = [
  { id_hash: 'hash-central', site_id: 'central' },
  { id_hash: 'hash-remote', site_id: 'remote_site' }
]

function makeCheckbox(checked: boolean): HTMLInputElement {
  const element = document.createElement('input')
  element.type = 'checkbox'
  element.checked = checked
  return element
}

function makeSelect(value: string): HTMLSelectElement {
  const element = document.createElement('select')
  const option = document.createElement('option')
  option.value = value
  element.appendChild(option)
  element.value = value
  return element
}

function makeDefault(text: string): HTMLDivElement {
  const element = document.createElement('div')
  element.textContent = text
  return element
}

describe('resolveSiteId', () => {
  test('uses the selected site when the attribute is set explicitly on the host', () => {
    const siteId = resolveSiteId(
      makeCheckbox(true),
      makeSelect('hash-remote'),
      makeDefault('central - Central Site'),
      sites
    )
    expect(siteId).toBe('remote_site')
  })

  test('uses the inherited folder site when the attribute is not set on the host', () => {
    // The disabled <select> still carries the central default, but the effective
    // value is shown in the default element. Regression test for the slideout
    // offering a registration command for the central site instead of the remote one.
    const siteId = resolveSiteId(
      makeCheckbox(false),
      makeSelect('hash-central'),
      makeDefault('remote_site - Remote Site Alias'),
      sites
    )
    expect(siteId).toBe('remote_site')
  })

  test('returns an empty string when the selected hash is unknown', () => {
    const siteId = resolveSiteId(
      makeCheckbox(true),
      makeSelect('hash-unknown'),
      makeDefault(''),
      sites
    )
    expect(siteId).toBe('')
  })

  test('returns an empty string when the inherited default element is empty', () => {
    const siteId = resolveSiteId(
      makeCheckbox(false),
      makeSelect('hash-central'),
      makeDefault(''),
      sites
    )
    expect(siteId).toBe('')
  })
})
