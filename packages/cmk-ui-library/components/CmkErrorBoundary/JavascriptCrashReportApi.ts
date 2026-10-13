/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { formatError } from 'cmk-ui-library/lib/error'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

const MAX_SHORT_TEXT_LENGTH = 1024
const MAX_URL_LENGTH = 8192
const MAX_LONG_TEXT_LENGTH = 64 * 1024

/** Progress of storing a caught error as a crash report, for display to the user. */
export type CrashReportState =
  | { status: 'none' }
  | { status: 'storing' }
  | { status: 'stored'; url: string }
  | { status: 'failed' }

/**
 * Stores an error caught in the browser as a crash report on the Checkmk site.
 *
 * An error that keeps being thrown, for example on every re-render, is stored
 * once per page load: repeated reports of it share the first attempt and its
 * resulting crash report URL. An attempt that failed is forgotten again, so a
 * later occurrence of the same error is free to try once more.
 */
export class JavascriptCrashReportApi {
  private readonly attempts = new Map<string, Promise<string>>()

  public report(error: Error, component: string, source: string): Promise<string> {
    const signature = [component, source, error.name, error.message, error.stack ?? ''].join('\n')
    let attempt = this.attempts.get(signature)
    if (attempt === undefined) {
      attempt = this.store(error, component, source)
      this.attempts.set(signature, attempt)
      attempt.catch(() => this.attempts.delete(signature))
    }
    return attempt
  }

  private async store(error: Error, component: string, source: string): Promise<string> {
    const created = unwrap(
      await client.POST('/domain-types/javascript_crash_report/collections/all', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          error_name: this.truncate(error.name, MAX_SHORT_TEXT_LENGTH),
          error_message: this.truncate(error.message, MAX_LONG_TEXT_LENGTH),
          url: this.truncate(window.location.href, MAX_URL_LENGTH),
          stack: this.truncate(error.stack ?? '', MAX_LONG_TEXT_LENGTH),
          component: this.truncate(component, MAX_SHORT_TEXT_LENGTH),
          context: this.truncate(
            [source, formatError(error)].filter(Boolean).join('\n\n'),
            MAX_LONG_TEXT_LENGTH
          )
        }
      })
    )
    return created.extensions.crash_report_url
  }

  private truncate(text: string, maxLength: number): string {
    return text.length > maxLength ? text.slice(0, maxLength) : text
  }
}
