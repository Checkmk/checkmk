<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import axios from 'axios'
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon'
import CmkLabel from '@/components/CmkLabel.vue'

import type { DashboardMetadata } from '@/dashboard-wip/types/dashboard.ts'
import { toPathAndSearch } from '@/dashboard-wip/utils.ts'

import ButtonDropdownMenu from './ButtonDropdownMenu.vue'
import DashboardSelector from './DashboardSelector.vue'
import MenuButton from './MenuButton.vue'
import type { SelectedDashboard } from './types'

interface Props {
  selectedDashboard: SelectedDashboard | null
  linkUserGuide: string
  linkNavigationEmbeddingPage: string
  isEditMode: boolean
}

const { _t } = usei18n()

const props = defineProps<Props>()

const emit = defineEmits<{
  'open-filter': []
  'open-settings': []
  'open-clone-workflow': []
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
  const dashboardName = props.selectedDashboard?.name
  if (!dashboardName) {
    console.error('No dashboard selected to set as start URL')
    return
  }
  console.log('Setting start URL to dashboard:', dashboardName)
  try {
    const url = 'ajax_set_dashboard_start_url.py'
    const response = await axios.post(url, null, {
      params: {
        name: dashboardName,
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

const pageNavigation = parsePageNavigation()
</script>

<template>
  <div class="dashboard-menu-header">
    <div class="left-section">
      <div class="dashboard-title">
        <CmkLabel class="dashboard-label">{{ _t('Dashboard') }}</CmkLabel>
        <CmkIcon name="info" size="small" class="info-icon" />
      </div>

      <div class="selection-section">
        <DashboardSelector
          :selected-dashboard="props.selectedDashboard"
          @dashboard-change="handleDashboardChange"
        />

        <MenuButton @click="emit('open-filter')">
          <CmkIcon name="filter" size="large" />
          <span>{{ _t('Filter') }}</span>
        </MenuButton>
      </div>
    </div>

    <div class="actions-section">
      <template v-if="!isEditMode">
        <ButtonDropdownMenu :label="_t('Settings Menu')">
          <template #button>
            <CmkIcon name="global-settings" size="large" />
            <span>{{ _t('Settings') }}</span>
          </template>
          <template #menu="{ hideMenu }">
            <div class="dropdown-menu-items">
              <div
                class="menu-item"
                @click="
                  () => {
                    emit('open-settings')
                    hideMenu()
                  }
                "
              >
                <div class="menu-label">{{ _t('Dashboard settings') }}</div>
              </div>

              <div
                class="menu-item"
                @click="
                  () => {
                    emit('open-clone-workflow')
                    hideMenu()
                  }
                "
              >
                <div class="menu-label">{{ _t('Clone dashboard') }}</div>
              </div>

              <a
                :href="linkUserGuide"
                class="menu-item menu-item--link"
                target="_blank"
                @click="hideMenu()"
              >
                <div class="menu-label">{{ _t('Dashboard user guide') }}</div>
                <CmkIcon name="external-link" size="small" />
              </a>

              <div
                class="menu-item"
                @click="
                  () => {
                    setStartUrl()
                    hideMenu()
                  }
                "
              >
                <div class="menu-label">{{ _t('Set as start URL') }}</div>
              </div>

              <a :href="pageNavigation.redirectLink" target="_top" class="no-underline">
                <div class="menu-item">
                  <div class="menu-label no-underline">{{ _t('Show page navigation') }}</div>
                  <div>
                    <CmkIcon :name="pageNavigation.toggle === 'on' ? 'toggle-on' : 'toggle-off'" />
                  </div>
                </div>
              </a>
            </div>
          </template>
        </ButtonDropdownMenu>

        <MenuButton class="menu-btn" @click="enterEditMode">
          <CmkIcon name="dashboard-grid" size="large" />
          <span>{{ _t('Edit widgets') }}</span>
        </MenuButton>
      </template>

      <template v-else>
        <div class="edit-mode-actions">
          <MenuButton variant="primary" @click="handleSave">
            {{ _t('Save') }}
          </MenuButton>

          <MenuButton @click="handleCancel">
            <CmkIcon name="cancel" />
            {{ _t('Cancel') }}
          </MenuButton>

          <MenuButton variant="secondary" @click="handleAddWidget">
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
.dropdown-menu-items {
  width: 100%;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .menu-item {
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: var(--dimension-5) var(--dimension-6);
    margin-bottom: var(--dimension-3);
    border: none;
    background: none;
    color: var(--font-color);
    font-size: var(--font-size-normal);
    text-align: left;
    text-decoration: none;
    cursor: pointer;
    border-radius: var(--dimension-3);
    transition: background-color 0.2s ease;

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    .menu-label {
      color: var(--font-color);
    }

    &:last-child {
      margin-bottom: 0;
    }

    &:hover {
      background-color: var(--ux-theme-5);
    }

    &--link {
      padding: 0;
      justify-content: flex-start;
    }
  }
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
