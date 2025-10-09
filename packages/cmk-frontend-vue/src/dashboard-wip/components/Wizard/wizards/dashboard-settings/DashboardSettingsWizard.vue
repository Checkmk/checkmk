<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { reactive, ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkTab from '@/components/CmkTabs/CmkTab.vue'
import CmkTabContent from '@/components/CmkTabs/CmkTabContent.vue'
import CmkTabs from '@/components/CmkTabs/CmkTabs.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import { type DashboardGeneralSettings } from '@/dashboard-wip/types/dashboard'

import ActionBar from '../../components/ActionBar.vue'
import ActionButton from '../../components/ActionButton.vue'
import ContentSpacer from '../../components/ContentSpacer.vue'
import { isIdInUse, isValidSnakeCase } from '../../components/DashboardSettings/utils'
import type { DashboardIcon } from '../create-dashboard/types'
import AccessSettings from './components/AccessSettings.vue'
import GeneralSettings from './components/GeneralSettings.vue'
import VisibilitySettings from './components/VisibilitySettings.vue'

const { _t } = usei18n()

const props = defineProps<{
  dashboardId: string
  dashboardGeneralSettings: DashboardGeneralSettings
  dashboardRestrictedToSingle: string[]
}>()

const emit = defineEmits<{
  save: [dashboardName: string, generalSettings: DashboardGeneralSettings]
  cancel: []
}>()

const uniqueId = ref<string>(props.dashboardId)
const generalSettings = reactive(props.dashboardGeneralSettings)

// //General
const originalId = uniqueId.value
const nameErrors = ref<string[]>([])
const createUniqueId = ref<boolean>(false)
const uniqueIdErrors = ref<string[]>([])
const dashboardTypeString =
  props.dashboardRestrictedToSingle.length === 0
    ? _t('Unrestricted')
    : props.dashboardRestrictedToSingle.join(', ')

const dashboardIcon = ref<string | null>(generalSettings.menu.icon?.name || null)
const dashboardEmblem = ref<string | null>(generalSettings.menu.icon?.emblem || null)

const openedTab = ref<string | number>('general')

const _nameValidation = (): [boolean, TranslatedString[]] => {
  if (generalSettings.title.text.trim() === '') {
    return [false, [_t('Name is required.')]]
  }
  return [true, []]
}

const _uniqueIdValidation = async (): Promise<[boolean, TranslatedString[]]> => {
  if (uniqueId.value.trim() === '') {
    return [false, [_t('Unique ID is required.')]]
  } else if (!isValidSnakeCase(uniqueId.value.trim())) {
    return [
      false,
      [
        _t(
          'Unique ID must only contain lowercase letters, numbers, and underscores, and must start with a letter.'
        )
      ]
    ]
  }

  if ((await isIdInUse(uniqueId.value.trim()), uniqueId.value)) {
    return [false, [_t('This Unique ID is already in use. Please choose another one.')]]
  }

  return [true, []]
}

const updateDescription = (val: string | null) => {
  if (val === null || val.trim() === '') {
    delete generalSettings.description
  } else {
    generalSettings.description = val.trim()
  }
}

const cancel = () => {
  emit('cancel')
}

const save = async () => {
  const [nameIsValid, nameValidationErrors] = _nameValidation()
  const [uniqueIdIsValid, uniqueIdValidationErrors] = await _uniqueIdValidation()

  nameErrors.value = nameValidationErrors
  uniqueIdErrors.value = uniqueIdValidationErrors

  if (nameIsValid && uniqueIdIsValid) {
    if (dashboardIcon.value !== null) {
      const icon: DashboardIcon = { name: dashboardIcon.value }
      if (dashboardEmblem.value !== null) {
        icon.emblem = dashboardEmblem.value
      }
      generalSettings.menu.icon = icon
    }

    emit('save', uniqueId.value.trim(), generalSettings)
  }
}
</script>

<template>
  <div class="db-settings-wizard__root">
    <div class="db-settings-wizard__container">
      <CmkHeading type="h1">
        {{ _t('Dashboard settings of %{name}', { name: generalSettings.title.text }) }}
      </CmkHeading>

      <ContentSpacer />

      <ActionBar align-items="left">
        <ActionButton :label="_t('Save')" :action="save" variant="primary" />

        <ActionButton
          :label="_t('Cancel')"
          :icon="{ name: 'cancel', side: 'left' }"
          :action="cancel"
          variant="secondary"
        />
      </ActionBar>

      <ContentSpacer />

      <CmkTabs v-model="openedTab">
        <template #tabs>
          <CmkTab id="general">{{ _t('General') }}</CmkTab>
          <CmkTab id="access">{{ _t('Access') }}</CmkTab>
          <CmkTab id="visibility">{{ _t('Visibility') }}</CmkTab>
        </template>
        <template #tab-contents>
          <CmkTabContent id="general" class="db-settings-wizard__box">
            <GeneralSettings
              v-model:name="generalSettings.title.text"
              v-model:add-filter-suffix="generalSettings.title.include_context"
              v-model:create-unique-id="createUniqueId"
              v-model:unique-id="uniqueId"
              v-model:dashboard-icon="dashboardIcon"
              v-model:dashboard-emblem="dashboardEmblem"
              :name-validation-errors="nameErrors"
              :description="generalSettings.description || null"
              :unique-id-validation-errors="uniqueIdErrors"
              :dashboard-type="dashboardTypeString"
              :original-dashboard-id="originalId"
              @update:description="updateDescription"
            />
          </CmkTabContent>
          <CmkTabContent id="access" class="db-settings-wizard__box">
            <AccessSettings v-model:share="generalSettings.visibility.share" />
          </CmkTabContent>
          <CmkTabContent id="visibility" class="db-settings-wizard__box">
            <VisibilitySettings
              v-model:monitor-menu="generalSettings.menu.topic"
              v-model:hide-in-monitor-menu="generalSettings.visibility.hide_in_monitor_menu"
              v-model:sort-index="generalSettings.menu.sort_index"
              v-model:hide-in-dropdowns-menu="generalSettings.visibility.hide_in_drop_down_menus"
              v-model:show-when-show-more-is-enabled="generalSettings.menu.is_show_more"
            />
          </CmkTabContent>
        </template>
      </CmkTabs>
    </div>
  </div>
</template>

<style scoped>
.db-settings-wizard__root {
  height: 95vh;
  overflow-y: auto;
  display: flex;
}

.db-settings-wizard__container {
  width: 100vh;
  flex: 2;
  padding: var(--spacing-double);
}

.db-settings-wizard__box {
  background-color: var(--ux-theme-2);
}
</style>
