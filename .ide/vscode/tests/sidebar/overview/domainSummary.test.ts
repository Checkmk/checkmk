/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as profileManager from '../../../src/profiles/profileManager'
import {
  enumerateIssues,
  getDomainSummary,
  sortIssues,
  summaryHeader
} from '../../../src/sidebar/overview/domainSummary'
import type { StateCache } from '../../../src/sidebar/types'

vi.mock('../../../src/profiles/profileManager', () => ({
  isActive: vi.fn()
}))

const mockedIsActive = vi.mocked(profileManager.isActive)

function emptyState(overrides: Partial<StateCache> = {}): StateCache {
  return {
    buildStatus: {},
    profiles: [],
    commands: {},
    pythonEnvsActive: false,
    environment: {
      python: '',
      pythonPath: '',
      node: '',
      pnpm: '',
      bazel: '',
      bazelisk: '',
      docker: '',
      gcc: '',
      pyenv: false,
      systemReady: false
    },
    extensionHealth: [],
    settingsMismatches: [],
    omdSites: [],
    activeProxies: [],
    devSiteTools: { installed: true, installedVersion: '1.0.0' },
    versionMismatch: null,
    onboarding: {
      systemDone: true,
      venvDone: true,
      ideDone: true,
      currentStep: null,
      allDone: true
    },
    onboardingDismissed: false,
    configInWorkspace: true,
    mypyTargets: {
      enabled: false,
      pythonProfileActive: false,
      activeCount: 0,
      catalogSize: 0,
      activeTargets: [],
      baselineTargets: [],
      alwaysOnTargets: [],
      stagedActiveAdd: [],
      stagedActiveRemove: [],
      stagedBaselineAdd: [],
      stagedBaselineRemove: [],
      dismissedPromptedTargets: [],
      catalog: []
    },
    allocator: {
      mode: 'default',
      libraryAvailable: false,
      recommendationDismissed: true,
      wrapperExists: false,
      dmypyExecutableMatches: false,
      runUsingInterpreterOff: false
    },
    pylanceHealth: {
      pid: null,
      rssMiB: null,
      thresholdMiB: 2048,
      overThreshold: false,
      extensionActive: false,
      monitored: false,
      inStartupGrace: false
    },
    gitState: {
      preCommitSkipping: false,
      preCommitDismissed: false,
      preCommitMissing: false,
      qaTestDataDirty: false
    },
    startupRegression: null,
    dmypyHealth: { running: false, stale: false, configMtimeMs: null, daemonStartMs: null },
    bazelCache: {
      sizeBytes: null,
      thresholdGiB: 50,
      cachePath: null,
      overThreshold: false
    },
    ...overrides
  }
}

beforeEach(() => {
  mockedIsActive.mockReset()
  mockedIsActive.mockReturnValue(false)
})

describe('enumerateIssues', () => {
  it('returns empty list for a healthy state', () => {
    expect(enumerateIssues(emptyState())).toEqual([])
  })

  it('flags stale venv build as critical (breaks mypy/Pylance)', () => {
    const issues = enumerateIssues(
      emptyState({
        buildStatus: {
          venv: { ok: false, label: 'Python venv', commandId: 'cmk.buildVenv' }
        }
      })
    )
    expect(issues).toHaveLength(1)
    expect(issues[0].id).toBe('build:venv')
    expect(issues[0].domain).toBe('build')
    expect(issues[0].severity).toBe('critical')
    expect(issues[0].label).toBe('Build · Python venv')
  })

  it('flags non-venv stale builds as warning', () => {
    const issues = enumerateIssues(
      emptyState({
        buildStatus: {
          cmkFrontend: { ok: false, label: 'cmk-frontend', commandId: 'cmk.buildCmkFrontend' }
        }
      })
    )
    expect(issues).toHaveLength(1)
    expect(issues[0].severity).toBe('warning')
  })

  it('surfaces inactive-profile-family setting drift as warning (not filtered)', () => {
    mockedIsActive.mockImplementation((f: string) => f === 'python')
    const issues = enumerateIssues(
      emptyState({
        settingsMismatches: [
          {
            key: 'python.foo',
            expected: true,
            actual: false,
            family: 'Python',
            scope: 'workspace'
          },
          { key: 'frontend.bar', expected: 1, actual: 2, family: 'UI', scope: 'workspace' }
        ]
      })
    )
    const byId = Object.fromEntries(issues.map((i) => [i.id, i]))
    expect(byId['settings:python.foo'].severity).toBe('critical')
    expect(byId['settings:frontend.bar'].severity).toBe('warning')
  })

  it('flags active-profile-family setting drift as critical', () => {
    mockedIsActive.mockImplementation((f: string) => f === 'python')
    const issues = enumerateIssues(
      emptyState({
        settingsMismatches: [
          { key: 'python.foo', expected: true, actual: false, family: 'Python', scope: 'workspace' }
        ]
      })
    )
    expect(issues).toHaveLength(1)
    expect(issues[0].severity).toBe('critical')
  })

  it('flags non-profile-family setting drift as warning', () => {
    mockedIsActive.mockReturnValue(false)
    const issues = enumerateIssues(
      emptyState({
        settingsMismatches: [
          {
            key: 'markdown.foo',
            expected: true,
            actual: false,
            family: 'Markdown',
            scope: 'workspace'
          }
        ]
      })
    )
    expect(issues).toHaveLength(1)
    expect(issues[0].severity).toBe('warning')
  })

  it('always counts non-profile-family mismatches regardless of active profiles', () => {
    mockedIsActive.mockReturnValue(false)
    const issues = enumerateIssues(
      emptyState({
        settingsMismatches: [
          {
            key: 'markdown.foo',
            expected: true,
            actual: false,
            family: 'Markdown',
            scope: 'workspace'
          },
          { key: 'cspell.bar', expected: 1, actual: 2, family: 'Spelling', scope: 'workspace' },
          { key: 'general.baz', expected: 'x', actual: 'y', family: 'General', scope: 'workspace' }
        ]
      })
    )
    expect(issues.map((i) => i.id).sort()).toEqual([
      'settings:cspell.bar',
      'settings:general.baz',
      'settings:markdown.foo'
    ])
  })

  it('missing required extension is critical when the family is active', () => {
    mockedIsActive.mockImplementation((f: string) => f === 'python')
    const issues = enumerateIssues(
      emptyState({
        extensionHealth: [
          {
            name: 'python',
            displayName: 'Python',
            required: true,
            extensions: [{ id: 'ms-pyright.pyright', installed: false }],
            allInstalled: false,
            installedCount: 0
          }
        ]
      })
    )
    expect(issues).toHaveLength(1)
    expect(issues[0].severity).toBe('critical')
    expect(issues[0].id).toBe('extension:ms-pyright.pyright')
  })

  it('missing required extension is only warning when its profile family is inactive', () => {
    mockedIsActive.mockReturnValue(false)
    const issues = enumerateIssues(
      emptyState({
        extensionHealth: [
          {
            name: 'rust',
            displayName: 'Rust',
            required: true,
            extensions: [{ id: 'rust-lang.rust-analyzer', installed: false }],
            allInstalled: false,
            installedCount: 0
          }
        ]
      })
    )
    expect(issues).toHaveLength(1)
    expect(issues[0].severity).toBe('warning')
  })

  it('flags Pylance over threshold as critical', () => {
    const issues = enumerateIssues(
      emptyState({
        pylanceHealth: {
          pid: 1,
          rssMiB: 2400,
          thresholdMiB: 2048,
          overThreshold: true,
          extensionActive: true,
          monitored: true
        }
      })
    )
    expect(issues).toHaveLength(1)
    expect(issues[0].severity).toBe('critical')
    expect(issues[0].id).toBe('pylance:over-threshold')
  })

  it('flags OMD auth as warning when any site status is unknown', () => {
    const issues = enumerateIssues(
      emptyState({
        omdSites: [
          {
            name: 's',
            dir: '/d',
            version: '',
            port: '',
            core: '',
            edition: '',
            status: { overall: -1, services: [] }
          }
        ]
      })
    )
    expect(issues[0].id).toBe('omd:auth')
    expect(issues[0].severity).toBe('warning')
  })

  it('flags OMD stopped sites as warning when no auth needed', () => {
    const issues = enumerateIssues(
      emptyState({
        omdSites: [
          {
            name: 'a',
            dir: '/d',
            version: '',
            port: '',
            core: '',
            edition: '',
            status: { overall: 0, services: [] }
          },
          {
            name: 'b',
            dir: '/d',
            version: '',
            port: '',
            core: '',
            edition: '',
            status: { overall: 1, services: [] }
          }
        ]
      })
    )
    expect(issues[0].id).toBe('omd:stopped')
    expect(issues[0].severity).toBe('warning')
  })
})

describe('sortIssues', () => {
  it('puts critical before warning', () => {
    const sorted = sortIssues([
      {
        id: 'w',
        domain: 'build',
        severity: 'warning',
        label: 'Build · x',
        description: '',
        tooltip: '',
        icon: 'tools'
      },
      {
        id: 'c',
        domain: 'pylance',
        severity: 'critical',
        label: 'Pylance memory',
        description: '',
        tooltip: '',
        icon: 'warning'
      }
    ])
    expect(sorted.map((i) => i.severity)).toEqual(['critical', 'warning'])
  })

  it('sorts alphabetically within the same severity and domain', () => {
    const sorted = sortIssues([
      {
        id: 'b',
        domain: 'build',
        severity: 'warning',
        label: 'Build · zebra',
        description: '',
        tooltip: '',
        icon: 'tools'
      },
      {
        id: 'a',
        domain: 'build',
        severity: 'warning',
        label: 'Build · alpha',
        description: '',
        tooltip: '',
        icon: 'tools'
      }
    ])
    expect(sorted.map((i) => i.label)).toEqual(['Build · alpha', 'Build · zebra'])
  })
})

describe('summaryHeader', () => {
  it('returns empty string when no issues', () => {
    expect(summaryHeader([])).toBe('')
  })

  it('reports both severities', () => {
    expect(
      summaryHeader([
        {
          id: 'a',
          domain: 'pylance',
          severity: 'critical',
          label: 'a',
          description: '',
          tooltip: '',
          icon: 'x'
        },
        {
          id: 'b',
          domain: 'build',
          severity: 'warning',
          label: 'b',
          description: '',
          tooltip: '',
          icon: 'x'
        },
        {
          id: 'c',
          domain: 'build',
          severity: 'warning',
          label: 'c',
          description: '',
          tooltip: '',
          icon: 'x'
        }
      ])
    ).toBe('1 critical · 2 warning')
  })
})

describe('getDomainSummary', () => {
  it('all-ok state returns overallSeverity=ok with totalIssues=0', () => {
    const s = getDomainSummary(emptyState())
    expect(s.overallSeverity).toBe('ok')
    expect(s.totalIssues).toBe(0)
    expect(s.builds.severity).toBe('ok')
    expect(s.settings.severity).toBe('ok')
    expect(s.omd.severity).toBe('ok')
    expect(s.health.severity).toBe('ok')
  })

  it('builds row is critical when venv is stale, warning when only non-venv is stale', () => {
    const critical = getDomainSummary(
      emptyState({
        buildStatus: {
          venv: { ok: false, label: 'Python venv', commandId: 'cmk.buildVenv' },
          fe: { ok: true, label: 'cmk-frontend', commandId: 'cmk.buildCmkFrontend' }
        }
      })
    )
    expect(critical.builds.severity).toBe('critical')
    expect(critical.builds.badge).toBe('1 stale')

    const warning = getDomainSummary(
      emptyState({
        buildStatus: {
          venv: { ok: true, label: 'Python venv', commandId: 'cmk.buildVenv' },
          fe: { ok: false, label: 'cmk-frontend', commandId: 'cmk.buildCmkFrontend' }
        }
      })
    )
    expect(warning.builds.severity).toBe('warning')
    expect(warning.builds.badge).toBe('1 stale')
  })

  it('escalates overall severity to critical when any chip is critical', () => {
    const s = getDomainSummary(
      emptyState({
        pylanceHealth: {
          pid: 1,
          rssMiB: 2400,
          thresholdMiB: 2048,
          overThreshold: true,
          extensionActive: true,
          monitored: true
        }
      })
    )
    expect(s.overallSeverity).toBe('critical')
    expect(s.health.severity).toBe('critical')
  })
})
