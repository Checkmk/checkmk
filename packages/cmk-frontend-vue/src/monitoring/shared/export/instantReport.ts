/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Opens the instant PDF report of a listing in a new tab: the columns it shows and the request
 * body it sends to its REST endpoint, which the report validates with that endpoint's own model.
 * They are posted as a form, as a large filter tree would not fit into the URL of a GET request.
 */
export class InstantReport {
  constructor(private readonly page: string) {}

  open(columns: readonly string[], body: object, extra: Record<string, string> = {}): void {
    const form = document.createElement('form')
    form.method = 'post'
    form.action = this.page
    form.target = '_blank'
    form.rel = 'noopener'
    const fields = { ...extra, cols: columns.join(','), body: JSON.stringify(body) }
    for (const [name, value] of Object.entries(fields)) {
      const input = document.createElement('input')
      input.type = 'hidden'
      input.name = name
      input.value = value
      form.appendChild(input)
    }
    document.body.appendChild(form)
    form.submit()
    form.remove()
  }
}
