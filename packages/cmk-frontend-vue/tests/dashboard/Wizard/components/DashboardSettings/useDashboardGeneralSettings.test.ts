/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'

import { useDashboardGeneralSettings } from '@/dashboard/components/Wizard/components/DashboardSettings/composables/useDashboardGeneralSettings.ts'
import type { DashboardGeneralSettings } from '@/dashboard/types/dashboard'

vi.mock('@/dashboard/components/Wizard/components/DashboardSettings/utils', () => ({
  isValidSnakeCase: (str: string) => /^[a-z0-9_]+$/.test(str),
  isIdInUse: async (owner: string, id: string) =>
    id === 'existing_dashboard' && owner === 'existing_user'
}))
describe('useDashboardGeneralSettings Composable', () => {
  describe('Initialization', () => {
    it('should initialize with default values when no initial settings provided', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      expect(settings.name.value).toBe('')
      expect(settings.uniqueId.value).toBe('')
      expect(settings.createUniqueId.value).toBe(true)
      expect(settings.addFilterSuffix.value).toBe(false)
      expect(settings.dashboardIcon.value).toBe(null)
      expect(settings.dashboardEmblem.value).toBe(null)
      expect(settings.showInMonitorMenu.value).toBe(false)
      expect(settings.sortIndex.value).toBe(99)
    })
    it('should initialize with provided settings', async () => {
      const initialSettings: DashboardGeneralSettings = {
        title: {
          text: 'My Dashboard',
          render: true,
          include_context: true
        },
        menu: {
          topic: 'monitoring',
          sort_index: 10,
          is_show_more: false,
          search_terms: [],
          icon: {
            name: 'icon-dashboard',
            emblem: 'emblem-important'
          }
        },
        visibility: {
          hide_in_monitor_menu: true,
          hide_in_drop_down_menus: false,
          share: 'no'
        }
      }
      const settings = await useDashboardGeneralSettings('nobody', initialSettings, 'dashboard_id')
      expect(settings.name.value).toBe('My Dashboard')
      expect(settings.uniqueId.value).toBe('dashboard_id')
      expect(settings.addFilterSuffix.value).toBe(true)
      expect(settings.dashboardIcon.value).toBe('icon-dashboard')
      expect(settings.dashboardEmblem.value).toBe('emblem-important')
      expect(settings.showInMonitorMenu.value).toBe(false)
      expect(settings.monitorMenuTopic.value).toBe('monitoring')
    })
  })
  describe('Name Validation', () => {
    it('should reject empty name during validation', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = ''
      await settings.validateGeneralSettings()
      expect(settings.nameErrors.value.length).toBeGreaterThan(0)
    })
    it('should accept non-empty name during validation', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = 'Valid Dashboard Name'
      await settings.validateGeneralSettings()
      expect(settings.nameErrors.value.length).toBe(0)
    })
    it('should clear previous name errors on revalidation with valid name', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = ''
      await settings.validateGeneralSettings()
      expect(settings.nameErrors.value.length).toBeGreaterThan(0)
      settings.name.value = 'Valid Name'
      await settings.validateGeneralSettings()
      expect(settings.nameErrors.value.length).toBe(0)
    })
  })
  describe('Unique ID Validation', () => {
    it('should reject empty unique ID', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.uniqueId.value = ''
      await settings.validateGeneralSettings()
      expect(settings.uniqueIdErrors.value.length).toBeGreaterThan(0)
    })
    it('should reject unique ID with invalid characters', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.uniqueId.value = 'Invalid-ID-With-Dashes'
      await settings.validateGeneralSettings()
      expect(settings.uniqueIdErrors.value.length).toBeGreaterThan(0)
    })
    it('should reject unique ID that is already in use by the user', async () => {
      const settings = await useDashboardGeneralSettings('existing_user')
      settings.uniqueId.value = 'existing_dashboard'
      await settings.validateGeneralSettings()
      expect(settings.uniqueIdErrors.value.length).toBeGreaterThan(0)
    })
    it('should accept unique ID that is already in use by another user', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.uniqueId.value = 'existing_dashboard'
      await settings.validateGeneralSettings()
      expect(settings.uniqueIdErrors.value.length).toBe(0)
    })
    it('should accept valid snake_case unique ID that is not in use', async () => {
      const settings = await useDashboardGeneralSettings('existing_user')
      settings.name.value = 'Dashboard'
      settings.uniqueId.value = 'valid_dashboard_id'
      const isValid = await settings.validateGeneralSettings()
      expect(settings.uniqueIdErrors.value.length).toBe(0)
      expect(isValid).toBe(true)
    })
    it('should accept unique ID that starts with number', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.uniqueId.value = '123_dashboard'
      await settings.validateGeneralSettings()
      expect(settings.uniqueIdErrors.value.length).toBe(0)
    })
    it('should accept unique ID that starts with underscore', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.uniqueId.value = '_dashboard'
      await settings.validateGeneralSettings()
      expect(settings.uniqueIdErrors.value.length).toBe(0)
    })
  })
  describe('Sort Index Validation', () => {
    it('should reject negative sort index', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = 'Dashboard'
      settings.uniqueId.value = 'dashboard_id'
      settings.sortIndex.value = -5
      await settings.validateGeneralSettings()
      expect(settings.sortIndexError.value.length).toBeGreaterThan(0)
    })
    it('should reject non-integer sort index', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = 'Dashboard'
      settings.uniqueId.value = 'dashboard_id'
      settings.sortIndex.value = 5.5
      await settings.validateGeneralSettings()
      expect(settings.sortIndexError.value.length).toBeGreaterThan(0)
    })
    it('should accept valid non-negative integer sort index', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = 'Dashboard'
      settings.uniqueId.value = 'dashboard_id'
      settings.sortIndex.value = 42
      const isValid = await settings.validateGeneralSettings()
      expect(settings.sortIndexError.value.length).toBe(0)
      expect(isValid).toBe(true)
    })
  })
  describe('Settings Building', () => {
    it('should build settings with all required fields and complete structure', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = 'Test Dashboard'
      settings.addFilterSuffix.value = true
      settings.showInMonitorMenu.value = true
      settings.monitorMenuTopic.value = 'monitoring'
      settings.sortIndex.value = 10
      const builtSettings = settings.buildSettings()

      expect(builtSettings).toEqual({
        title: {
          text: 'Test Dashboard',
          render: true,
          include_context: true
        },
        menu: {
          topic: 'monitoring',
          sort_index: 10,
          is_show_more: false,
          search_terms: []
        },
        visibility: {
          hide_in_monitor_menu: false,
          hide_in_drop_down_menus: false,
          share: 'no'
        }
      })
    })
    it('should include icon in settings when icon is set with complete structure', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = 'Dashboard'
      settings.dashboardIcon.value = 'icon-chart'
      const builtSettings = settings.buildSettings()

      expect(builtSettings).toEqual({
        title: {
          text: 'Dashboard',
          render: true,
          include_context: false
        },
        menu: {
          topic: 'other',
          sort_index: 99,
          is_show_more: false,
          search_terms: [],
          icon: {
            name: 'icon-chart'
          }
        },
        visibility: {
          hide_in_monitor_menu: true,
          hide_in_drop_down_menus: false,
          share: 'no'
        }
      })
    })
    it('should include emblem in icon when both icon and emblem are set with complete structure', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = 'Dashboard'
      settings.dashboardIcon.value = 'icon-chart'
      settings.dashboardEmblem.value = 'emblem-warning'
      const builtSettings = settings.buildSettings()

      expect(builtSettings).toEqual({
        title: {
          text: 'Dashboard',
          render: true,
          include_context: false
        },
        menu: {
          topic: 'other',
          sort_index: 99,
          is_show_more: false,
          search_terms: [],
          icon: {
            name: 'icon-chart',
            emblem: 'emblem-warning'
          }
        },
        visibility: {
          hide_in_monitor_menu: true,
          hide_in_drop_down_menus: false,
          share: 'no'
        }
      })
    })
    it('should not include icon in settings when icon is not set', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = 'Dashboard'
      settings.dashboardIcon.value = null
      const builtSettings = settings.buildSettings()
      expect(builtSettings.menu.icon).toBeUndefined()
    })
    it('should default to "other" topic when none specified', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = 'Dashboard'
      settings.monitorMenuTopic.value = ''
      const builtSettings = settings.buildSettings()
      expect(builtSettings.menu.topic).toBe('other')
    })
    it('should hide dashboard in monitor menu when showInMonitorMenu is false', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = 'Dashboard'
      settings.showInMonitorMenu.value = false
      const builtSettings = settings.buildSettings()
      expect(builtSettings.visibility.hide_in_monitor_menu).toBe(true)
    })
  })
  describe('Complete Validation Flow', () => {
    it('should return false when validation fails', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = ''
      const isValid = await settings.validateGeneralSettings()
      expect(isValid).toBe(false)
    })
    it('should return true when all validations pass', async () => {
      const settings = await useDashboardGeneralSettings('nobody')
      settings.name.value = 'Valid Dashboard'
      settings.uniqueId.value = 'valid_dashboard'
      settings.sortIndex.value = 10
      const isValid = await settings.validateGeneralSettings()
      expect(isValid).toBe(true)
    })
  })
})
