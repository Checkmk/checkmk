/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { type SettingsEntry, buildEffectiveSettings } from '../../src/build/settings'
import * as profileManager from '../../src/profiles/profileManager'

vi.mock('../../src/profiles/profileManager', () => ({
  isActive: vi.fn()
}))

const mockedIsActive = vi.mocked(profileManager.isActive)

beforeEach(() => {
  mockedIsActive.mockReset()
})

describe('buildEffectiveSettings', () => {
  const baseEntry: SettingsEntry = {
    folder: { 'editor.fontSize': 14 as any, 'python.analysis.enabled': true as any },
    workspace: { 'files.autoSave': 'afterDelay' as any },
    user: { 'editor.theme': 'dark' as any }
  }

  it('returns settings unchanged when extensionSets is null', () => {
    const result = buildEffectiveSettings(baseEntry, 'test', null)
    expect(result.folderSettings).toEqual({
      'editor.fontSize': 14,
      'python.analysis.enabled': true
    })
    expect(result.workspaceSettings).toEqual({ 'files.autoSave': 'afterDelay' })
    expect(result.userSettings).toEqual({ 'editor.theme': 'dark' })
  })

  it('preserves settings for active profiles', () => {
    mockedIsActive.mockReturnValue(true)

    const extensionSets = {
      python: {
        extensions: ['ms-python.python'],
        disableSettings: { 'python.analysis.enabled': false }
      }
    }

    const result = buildEffectiveSettings(baseEntry, 'test', extensionSets)
    expect(result.folderSettings['python.analysis.enabled']).toBe(true)
  })

  it('applies disable-settings for inactive profiles', () => {
    mockedIsActive.mockReturnValue(false)

    const extensionSets = {
      python: {
        extensions: ['ms-python.python'],
        disableSettings: { 'python.analysis.enabled': false }
      }
    }

    const result = buildEffectiveSettings(baseEntry, 'test', extensionSets)
    expect(result.folderSettings['python.analysis.enabled']).toBe(false)
  })

  it('only overrides keys that exist in the original settings', () => {
    mockedIsActive.mockReturnValue(false)

    const extensionSets = {
      python: {
        extensions: ['ms-python.python'],
        disableSettings: { 'python.analysis.enabled': false, 'python.linting': false }
      }
    }

    const result = buildEffectiveSettings(baseEntry, 'test', extensionSets)
    expect(result.folderSettings['python.analysis.enabled']).toBe(false)
    expect(result.folderSettings).not.toHaveProperty('python.linting')
  })

  it('handles array extension entries (no disableSettings)', () => {
    mockedIsActive.mockReturnValue(false)

    const extensionSets = {
      bazel: ['bazelbuild.vscode-bazel']
    }

    const result = buildEffectiveSettings(baseEntry, 'test', extensionSets as any)
    expect(result.folderSettings).toEqual({
      'editor.fontSize': 14,
      'python.analysis.enabled': true
    })
  })

  it('handles empty settings entry', () => {
    const result = buildEffectiveSettings({}, 'test', null)
    expect(result.folderSettings).toEqual({})
    expect(result.workspaceSettings).toEqual({})
    expect(result.userSettings).toEqual({})
  })
})
