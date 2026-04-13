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

    const entry: SettingsEntry = {
      ...baseEntry,
      disableFolder: { 'python.analysis.enabled': false as any }
    }

    const result = buildEffectiveSettings(entry, 'test', null)
    expect(result.folderSettings['python.analysis.enabled']).toBe(true)
  })

  it('applies disableFolder for inactive profiles', () => {
    mockedIsActive.mockReturnValue(false)

    const entry: SettingsEntry = {
      ...baseEntry,
      disableFolder: { 'python.analysis.enabled': false as any }
    }

    const result = buildEffectiveSettings(entry, 'test', null)
    expect(result.folderSettings['python.analysis.enabled']).toBe(false)
  })

  it('applies disableWorkspace for inactive profiles', () => {
    mockedIsActive.mockReturnValue(false)

    const entry: SettingsEntry = {
      ...baseEntry,
      disableWorkspace: { 'files.autoSave': 'off' as any }
    }

    const result = buildEffectiveSettings(entry, 'test', null)
    expect(result.workspaceSettings['files.autoSave']).toBe('off')
  })

  it('applies disableUser for inactive profiles', () => {
    mockedIsActive.mockReturnValue(false)

    const entry: SettingsEntry = {
      ...baseEntry,
      disableUser: { 'editor.theme': 'light' as any }
    }

    const result = buildEffectiveSettings(entry, 'test', null)
    expect(result.userSettings['editor.theme']).toBe('light')
  })

  it('adds new keys from disable settings', () => {
    mockedIsActive.mockReturnValue(false)

    const entry: SettingsEntry = {
      ...baseEntry,
      disableFolder: { 'python.linting': false as any }
    }

    const result = buildEffectiveSettings(entry, 'test', null)
    expect(result.folderSettings['python.linting']).toBe(false)
  })

  it('handles empty settings entry', () => {
    const result = buildEffectiveSettings({}, 'test', null)
    expect(result.folderSettings).toEqual({})
    expect(result.workspaceSettings).toEqual({})
    expect(result.userSettings).toEqual({})
  })
})
