/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import { type DashboardGeneralSettings } from '@/dashboard-wip/types/dashboard'

import type { DashboardIcon } from '../types'
import { isIdInUse, isValidSnakeCase } from '../utils'

const { _t } = usei18n()

export function useDashboardGeneralSettings() {
  // --- General ---
  const name = ref<string>('')
  const nameErrors = ref<string[]>([])

  const createUniqueId = ref<boolean>(true)
  const uniqueId = ref<string>('')
  const uniqueIdErrors = ref<string[]>([])

  const dashboardIcon = ref<string | null>(null)
  const dashboardEmblem = ref<string | null>(null)

  // --- Visibility ---
  const showInMonitorMenu = ref<boolean>(false)
  const monitorMenu = ref<string>('dashboards')
  const sortIndex = ref<number>(99)

  // --- Validation ---
  const validateName = () => {
    nameErrors.value = []
    if (name.value.trim() === '') {
      nameErrors.value.push(_t('Name is required.'))
    }
  }

  const validateUniqueId = async () => {
    uniqueIdErrors.value = []

    const trimmed = uniqueId.value.trim()
    if (trimmed === '') {
      uniqueIdErrors.value.push(_t('Unique ID is required.'))
      return
    }

    if (!isValidSnakeCase(trimmed)) {
      uniqueIdErrors.value.push(
        _t(
          'Unique ID must only contain lowercase letters, numbers, and underscores, and must start with a letter.'
        )
      )
      return
    }

    if (await isIdInUse(trimmed)) {
      uniqueIdErrors.value.push(_t('This Unique ID is already in use. Please choose another one.'))
    }
  }

  const validateGeneralSettings = async (): Promise<boolean> => {
    validateName()
    await validateUniqueId()
    return nameErrors.value.length + uniqueIdErrors.value.length === 0
  }

  const buildSettings = (): DashboardGeneralSettings => {
    const title = {
      text: name.value.trim(),
      render: true,
      include_context: false
    }

    const menu: DashboardGeneralSettings['menu'] = {
      topic: showInMonitorMenu.value ? monitorMenu.value : 'other',
      sort_index: sortIndex.value,
      is_show_more: false,
      search_terms: []
    }

    if (dashboardIcon.value) {
      const icon: DashboardIcon = {
        name: dashboardIcon.value
      }
      if (dashboardEmblem.value) {
        icon.emblem = dashboardEmblem.value
      }

      menu.icon = icon
    }

    const visibility: DashboardGeneralSettings['visibility'] = {
      hide_in_monitor_menu: !showInMonitorMenu.value,
      hide_in_drop_down_menus: false,
      share: 'no'
    }

    return { title, menu, visibility }
  }

  return {
    name,
    nameErrors,
    createUniqueId,
    uniqueId,
    uniqueIdErrors,
    dashboardIcon,
    dashboardEmblem,
    showInMonitorMenu,
    monitorMenu,
    sortIndex,

    validateGeneralSettings,
    buildSettings
  }
}

export type DashboardGeneralSettingsConfiguration = ReturnType<typeof useDashboardGeneralSettings>
