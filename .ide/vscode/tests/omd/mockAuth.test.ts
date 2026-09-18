/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { probeHttp, waitForHttp } from '../../src/core/http'
import { runCommand } from '../../src/core/tasks'
import { ensureMockAuthRunning, hasCloudSite } from '../../src/omd/mockAuth'
import type { OmdSite } from '../../src/omd/omd'

vi.mock('../../src/core/http', () => ({
  probeHttp: vi.fn(),
  waitForHttp: vi.fn()
}))

vi.mock('../../src/core/tasks', () => ({
  runCommand: vi.fn(() => ({}))
}))

function site(edition: string): OmdSite {
  return {
    name: `v${edition}`,
    dir: '/omd/sites/x',
    version: `2.5.0.${edition}`,
    port: '',
    core: '',
    edition
  }
}

describe('hasCloudSite', () => {
  it('matches the legacy cloud and saas edition suffixes', () => {
    expect(hasCloudSite([site('cee'), site('cce')])).toBe(true)
    expect(hasCloudSite([site('cse')])).toBe(true)
  })

  it('matches the long-form cloud edition name', () => {
    expect(hasCloudSite([site('cloud')])).toBe(true)
  })

  it('is false without a cloud site', () => {
    expect(hasCloudSite([site('pro'), site('cee'), site('community')])).toBe(false)
  })

  it('is false without any site', () => {
    expect(hasCloudSite([])).toBe(false)
  })
})

describe('ensureMockAuthRunning', () => {
  beforeEach(() => {
    vi.mocked(probeHttp).mockReset()
    vi.mocked(waitForHttp).mockReset()
    vi.mocked(runCommand).mockClear()
  })

  it('does not start a second server when one already answers', async () => {
    vi.mocked(probeHttp).mockResolvedValue(true)

    await expect(ensureMockAuthRunning()).resolves.toBe(true)
    expect(runCommand).not.toHaveBeenCalled()
  })

  it('starts the server and waits for it when the port is silent', async () => {
    vi.mocked(probeHttp).mockResolvedValue(false)
    vi.mocked(waitForHttp).mockResolvedValue(true)

    await expect(ensureMockAuthRunning()).resolves.toBe(true)
    expect(vi.mocked(runCommand).mock.calls[0][1]).toBe('cmk-dev-site-mock-auth')
    expect(vi.mocked(waitForHttp).mock.calls[0][0]).toBe('http://127.0.0.1:8089/healthz')
  })

  it('reports failure when the server never comes up', async () => {
    vi.mocked(probeHttp).mockResolvedValue(false)
    vi.mocked(waitForHttp).mockResolvedValue(false)

    await expect(ensureMockAuthRunning()).resolves.toBe(false)
  })
})
