/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, expect, test, vi } from 'vitest'

import { InstantReport } from '@/monitoring/shared/export/instantReport'

interface PostedForm {
  method: string
  action: string
  target: string
  fields: Record<string, string>
}

function capturePostedForms(): PostedForm[] {
  const posted: PostedForm[] = []
  vi.spyOn(HTMLFormElement.prototype, 'submit').mockImplementation(function (
    this: HTMLFormElement
  ) {
    posted.push({
      method: this.method,
      action: this.getAttribute('action') ?? '',
      target: this.target,
      fields: Object.fromEntries(
        [...new FormData(this).entries()].map(([name, value]) => [name, String(value)])
      )
    })
  })
  return posted
}

afterEach(() => {
  vi.restoreAllMocks()
})

test('posts the shown columns and the request body to the report page in a new tab', () => {
  const posted = capturePostedForms()

  new InstantReport('report_instant_all_hosts.py').open(['state', 'name'], {
    limit: null,
    sort: ['name:asc']
  })

  expect(posted).toEqual([
    {
      method: 'post',
      action: 'report_instant_all_hosts.py',
      target: '_blank',
      fields: { cols: 'state,name', body: JSON.stringify({ limit: null, sort: ['name:asc'] }) }
    }
  ])
})

test('adds the parameters a report needs beyond the listing', () => {
  const posted = capturePostedForms()

  new InstantReport('report_instant_host_services.py').open(
    ['name'],
    {},
    {
      host: 'web-1',
      site: 'local'
    }
  )

  expect([posted[0]!.fields.host, posted[0]!.fields.site]).toEqual(['web-1', 'local'])
})

test('leaves no form behind', () => {
  capturePostedForms()

  new InstantReport('report_instant_all_hosts.py').open(['name'], {})

  expect(document.querySelector('form')).toBeNull()
})
