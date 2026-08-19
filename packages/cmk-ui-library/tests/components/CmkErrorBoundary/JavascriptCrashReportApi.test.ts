/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { JavascriptCrashReportApi } from 'cmk-ui-library/components/CmkErrorBoundary/JavascriptCrashReportApi'
import { CmkError } from 'cmk-ui-library/lib/error'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const CRASH_REPORT_URL = '/domain-types/javascript_crash_report/collections/all'

describe('JavascriptCrashReportApi.report', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let postSpy: any

  beforeEach(() => {
    postSpy = vi.spyOn(client, 'POST')
    postSpy.mockResolvedValue({
      data: {
        domainType: 'javascript_crash_report',
        id: 'a-crash-id',
        links: [],
        extensions: {
          crash_type: 'javascript',
          crash_report_url: 'crash.py?component=javascript&ident=a-crash-id'
        }
      },
      error: undefined,
      response: new Response(null, { status: 201 })
    } as never)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function makeError(message: string): Error {
    const error = new TypeError(message)
    error.stack = `TypeError: ${message}\n    at renderTile (http://localhost/js/main.js:12:3)`
    return error
  }

  it('posts the error together with the page it happened on', async () => {
    await new JavascriptCrashReportApi().report(
      makeError('boom'),
      'DashboardApp',
      'render function'
    )

    expect(postSpy).toHaveBeenCalledTimes(1)
    expect(postSpy).toHaveBeenCalledWith(CRASH_REPORT_URL, {
      params: { header: { 'Content-Type': 'application/json' } },
      body: {
        error_name: 'TypeError',
        error_message: 'boom',
        url: window.location.href,
        stack: 'TypeError: boom\n    at renderTile (http://localhost/js/main.js:12:3)',
        component: 'DashboardApp',
        context: expect.stringContaining('render function')
      }
    })
  })

  it('includes the context of a CmkError cause chain', async () => {
    class ApiError extends CmkError {
      override getContext(): string {
        return 'STATUS 500: internal error'
      }
    }
    const error = new CmkError('loading failed', new ApiError('request failed', null))

    await new JavascriptCrashReportApi().report(error, '', 'setup function')

    expect(postSpy.mock.calls[0][1].body.context).toContain('STATUS 500: internal error')
  })

  it('returns the URL of the stored crash report', async () => {
    const url = await new JavascriptCrashReportApi().report(
      makeError('boom'),
      'DashboardApp',
      'render function'
    )

    expect(url).toBe('crash.py?component=javascript&ident=a-crash-id')
  })

  it('stores the same error only once and reuses its crash report', async () => {
    const api = new JavascriptCrashReportApi()

    const first = await api.report(makeError('boom'), 'DashboardApp', 'render function')
    const second = await api.report(makeError('boom'), 'DashboardApp', 'render function')

    expect(postSpy).toHaveBeenCalledTimes(1)
    expect(second).toBe(first)
  })

  it('does not send the same error twice while the first attempt is in flight', async () => {
    const api = new JavascriptCrashReportApi()

    await Promise.all([
      api.report(makeError('boom'), 'DashboardApp', 'render function'),
      api.report(makeError('boom'), 'DashboardApp', 'render function')
    ])

    expect(postSpy).toHaveBeenCalledTimes(1)
  })

  it('tries again on the next occurrence when storing failed', async () => {
    const api = new JavascriptCrashReportApi()
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 500, statusText: 'Internal Server Error' })
    } as never)

    await expect(api.report(makeError('boom'), 'DashboardApp', 'render function')).rejects.toThrow()
    const url = await api.report(makeError('boom'), 'DashboardApp', 'render function')

    expect(postSpy).toHaveBeenCalledTimes(2)
    expect(url).toBe('crash.py?component=javascript&ident=a-crash-id')
  })

  it('reports a different error again', async () => {
    const api = new JavascriptCrashReportApi()

    await api.report(makeError('boom'), 'DashboardApp', 'render function')
    await api.report(makeError('other boom'), 'DashboardApp', 'render function')

    expect(postSpy).toHaveBeenCalledTimes(2)
  })

  it('truncates an oversized stack so the site accepts the report', async () => {
    const error = makeError('boom')
    error.stack = 'a'.repeat(64 * 1024 + 100)

    await new JavascriptCrashReportApi().report(error, '', 'render function')

    expect(postSpy.mock.calls[0][1].body.stack).toHaveLength(64 * 1024)
  })

  it('keeps a long view URL with its whole filter context', async () => {
    const originalUrl = window.location.href
    const filterContext = `?view_name=allhosts&${'host_regex=a&'.repeat(300)}`
    window.history.replaceState({}, '', `/NO_SITE/check_mk/view.py${filterContext}`)
    expect(window.location.href.length).toBeGreaterThan(1024)

    await new JavascriptCrashReportApi().report(makeError('boom'), '', 'render function')
    window.history.replaceState({}, '', originalUrl)

    expect(postSpy.mock.calls[0][1].body.url).toContain('host_regex=a')
    expect(postSpy.mock.calls[0][1].body.url.length).toBeGreaterThan(1024)
  })

  it('truncates a URL longer than the site accepts', async () => {
    const originalUrl = window.location.href
    window.history.replaceState({}, '', `/?${'a'.repeat(8192)}`)

    await new JavascriptCrashReportApi().report(makeError('boom'), '', 'render function')
    window.history.replaceState({}, '', originalUrl)

    expect(postSpy.mock.calls[0][1].body.url).toHaveLength(8192)
  })

  it('throws when the site did not accept the report', async () => {
    postSpy.mockResolvedValue({
      data: undefined,
      error: {},
      response: new Response('', { status: 403, statusText: 'Forbidden' })
    } as never)

    await expect(
      new JavascriptCrashReportApi().report(makeError('boom'), '', 'render function')
    ).rejects.toThrow()
  })
})
