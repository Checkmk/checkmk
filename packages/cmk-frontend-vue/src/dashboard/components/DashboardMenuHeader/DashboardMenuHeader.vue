<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import axios from 'axios'
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon'
import CmkLabel from '@/components/CmkLabel.vue'

import {
  type DashboardMetadata,
  DashboardOwnerType,
  type DashboardTokenModel
} from '@/dashboard/types/dashboard.ts'
import { copyToClipboard, toPathAndSearch, urlHandler } from '@/dashboard/utils.ts'

import DashboardSelector from './DashboardSelector.vue'
import DropdownMenu from './DropdownMenu.vue'
import MenuButton from './MenuButton.vue'
import SharingStatus from './SharingStatus.vue'
import type { SelectedDashboard } from './types'

interface Props {
  selectedDashboard: SelectedDashboard | null
  canEditDashboard: boolean
  linkUserGuide: string
  linkNavigationEmbeddingPage: string
  isEditMode: boolean
  publicToken: DashboardTokenModel | null
  isEmptyDashboard: boolean
  isDashboardLoading: boolean
}

const { _t } = usei18n()

const props = defineProps<Props>()

const emit = defineEmits<{
  'open-runtime-filter': []
  'open-filter-settings': []
  'open-settings': []
  'open-clone-workflow': []
  'open-share-workflow': []
  'open-widget-workflow': []
  save: []
  'enter-edit': []
  'cancel-edit': []
  'set-dashboard': [dashboard: DashboardMetadata]
}>()

const showDashboardDropdown = ref(false)

const handleDashboardChange = (dashboard: DashboardMetadata) => {
  emit('set-dashboard', dashboard)
  showDashboardDropdown.value = false
}

const enterEditMode = () => {
  emit('enter-edit')
}

const handleSave = () => {
  emit('save')
}

const handleCancel = () => {
  emit('cancel-edit')
}

const handleAddWidget = () => {
  emit('open-widget-workflow')
}

const setStartUrl = async (): Promise<void> => {
  const dashboard = props.selectedDashboard
  if (!dashboard) {
    console.error('No dashboard selected to set as start URL')
    return
  }
  try {
    const url = 'ajax_set_dashboard_start_url.py'
    const response = await axios.post(url, null, {
      params: {
        name: dashboard.name,
        owner: dashboard.owner,
        // @ts-expect-error  TODO change if something is implemented to use CSRF token
        _csrf_token: global_csrf_token
      }
    })

    if (response.data.result_code !== 0) {
      console.error('Error setting start URL:', response.data.result)
    }
  } catch (error) {
    console.error('Request failed:', error)
  }
}

const parsePageNavigation = () => {
  let redirectLink
  let toggle
  if (window.self !== window.top) {
    // inside the embedding iframe which show the page nagivation
    redirectLink = window.location.href
    toggle = 'on'
  } else {
    redirectLink = `${props.linkNavigationEmbeddingPage}?start_url=${toPathAndSearch(new URL(window.location.href))}`
    toggle = 'off'
  }
  return {
    redirectLink,
    toggle
  }
}

const isBuiltInDashboard = computed(
  () => props.selectedDashboard?.type === DashboardOwnerType.BUILT_IN
)

const isInteractionDisabled = computed(() => props.isDashboardLoading || !props.selectedDashboard)

const copyInternalDashboardLink = async (): Promise<void> => {
  const url = window?.parent?.location?.href || window.location.href
  await copyToClipboard(url)
}

const pageNavigation = parsePageNavigation()
</script>

<template>
  <div class="dashboard-menu-header">
    <div class="left-section">
      <div class="dashboard-title">
        <CmkLabel class="dashboard-label">{{ _t('Dashboard') }}</CmkLabel>
      </div>

      <div class="selection-section">
        <DashboardSelector
          :selected-dashboard="props.selectedDashboard"
          :disabled="props.isDashboardLoading"
          @dashboard-change="handleDashboardChange"
        />

        <MenuButton
          v-if="!isEditMode"
          :disabled="isInteractionDisabled"
          @click="emit('open-runtime-filter')"
        >
          <CmkIcon name="filter" size="large" />
          <span>{{ _t('Filter') }}</span>
        </MenuButton>
      </div>
    </div>

    <div class="actions-section">
      <template v-if="!isEditMode">
        <SharingStatus
          v-if="canEditDashboard && !isBuiltInDashboard"
          :enabled="!!publicToken"
          :shared-until="publicToken?.expires_at ? new Date(publicToken?.expires_at) : null"
          @open-sharing-settings="emit('open-share-workflow')"
        />

        <DropdownMenu
          icon="export-link"
          :label="_t('Share')"
          :disabled="isInteractionDisabled"
          :options="[
            { label: _t('Copy internal link'), action: copyInternalDashboardLink },
            {
              label: _t('Copy public link'),
              hidden: isBuiltInDashboard || !canEditDashboard,
              disabled: !publicToken,
              action: () => {
                copyToClipboard(urlHandler.getSharedDashboardLink(publicToken!.token_id))
              }
            },
            {
              label: _t('Configure sharing'),
              action: () => {
                emit('open-share-workflow')
              },
              hidden: isBuiltInDashboard || !canEditDashboard
            },
            {
              label: _t('Clone dashboard to generate public link'),
              action: () => emit('open-clone-workflow'),
              hidden: !isBuiltInDashboard || !canEditDashboard
            }
          ]"
        />

        <DropdownMenu
          icon="global-settings"
          :label="_t('Settings')"
          :right="!(isBuiltInDashboard || canEditDashboard)"
          :disabled="isInteractionDisabled"
          :options="[
            {
              label: _t('Dashboard settings'),
              action: () => emit('open-settings'),
              hidden: isBuiltInDashboard || !canEditDashboard
            },
            {
              label: _t('Filter settings'),
              action: () => emit('open-filter-settings'),
              hidden: isBuiltInDashboard || !canEditDashboard
            },
            { label: _t('Clone dashboard'), action: () => emit('open-clone-workflow') },
            {
              label: _t('Dashboard user guide'),
              url: linkUserGuide,
              target: '_blank',
              icon: 'external'
            },
            { label: _t('Set as start URL'), action: () => setStartUrl() },
            {
              label: _t('Show page navigation'),
              url: pageNavigation.redirectLink,
              target: '_top',
              icon: pageNavigation.toggle === 'on' ? 'toggle-on' : 'toggle-off'
            }
          ]"
        />

        <MenuButton
          v-if="isBuiltInDashboard"
          :disabled="isInteractionDisabled"
          @click="emit('open-clone-workflow')"
        >
          <CmkIcon name="clone" size="large" />
          <span>{{ _t('Clone') }}</span>
        </MenuButton>

        <MenuButton
          v-else-if="canEditDashboard"
          class="menu-btn"
          :disabled="isInteractionDisabled"
          @click="isEmptyDashboard ? handleAddWidget() : enterEditMode()"
        >
          <CmkIcon name="dashboard-grid" size="large" />
          <span>{{ isEmptyDashboard ? _t('Add widget') : _t('Edit widgets') }}</span>
        </MenuButton>
      </template>

      <template v-else>
        <div class="edit-mode-actions">
          <MenuButton variant="primary" :disabled="isInteractionDisabled" @click="handleSave">
            {{ _t('Save') }}
          </MenuButton>

          <MenuButton :disabled="isInteractionDisabled" @click="handleCancel">
            <CmkIcon name="cancel" />
            {{ _t('Cancel') }}
          </MenuButton>

          <MenuButton
            variant="secondary"
            :disabled="isInteractionDisabled"
            @click="handleAddWidget"
          >
            <CmkIcon name="plus" />
            {{ _t('Add widget') }}
          </MenuButton>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: transparent;
  color: var(--font-color);
  padding: var(--dimension-4);
  font-size: var(--font-size-large);
  min-height: 48px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.left-section {
  display: flex;
  align-items: center;
  gap: var(--dimension-6);
  flex: 1;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .selection-section {
    display: flex;
    align-items: center;
    gap: var(--dimension-4);
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-title {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-label {
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-xxlarge);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.no-underline {
  text-decoration: none !important;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.actions-section {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  flex: 1;
  justify-content: flex-end;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.edit-mode-actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}
</style>
