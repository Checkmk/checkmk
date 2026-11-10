<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import axios from 'axios'
import type { DrillUpButton as DrillUp } from 'cmk-shared-typing/typescript/drill_up_button'
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker.ts'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time/types.ts'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { kioskMode } from 'cmk-ui-library/lib/kiosk'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, ref } from 'vue'

import { getCsrfToken } from '@/lib/csrf'

import {
  type DashboardMetadata,
  DashboardOwnerType,
  type DashboardTokenModel
} from '@/dashboard/types/dashboard.ts'
import { copyToClipboard, urlHandler } from '@/dashboard/utils.ts'
import GlobalTimePicker from '@/graphing/GlobalTimePicker/GlobalTimePicker.vue'
import DrillUpButton from '@/page-header/DrillUpButton.vue'

import DashboardSelector from './DashboardSelector.vue'
import DropdownMenu from './DropdownMenu.vue'
import MenuButton from './MenuButton.vue'
import SharingStatus, { type SharingState } from './SharingStatus.vue'
import type { SelectedDashboard } from './types'

interface Props {
  selectedDashboard: SelectedDashboard | null
  canEditDashboard: boolean
  canCloneAsResponsive: boolean
  linkUserGuide: string
  isEditMode: boolean
  publicToken: DashboardTokenModel | null
  isEmptyDashboard: boolean
  isDashboardLoading: boolean
  runtimeFilters: Record<string, string>
  globalTimePicker: GlobalTimePickerProps
  drillUp?: DrillUp | null
}

const { _t } = usei18n()

const props = defineProps<Props>()

const emit = defineEmits<{
  'open-runtime-filter': []
  'open-filter-settings': []
  'open-settings': []
  'open-clone-workflow': []
  'open-responsive-clone-workflow': []
  'open-share-workflow': []
  'open-widget-workflow': []
  save: []
  'enter-edit': []
  'cancel-edit': []
  'set-dashboard': [dashboard: DashboardMetadata]
}>()

const range = defineModel<DateTimeRange>('range', { required: true })

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
        _csrf_token: getCsrfToken()
      }
    })

    if (response.data.result_code !== 0) {
      console.error('Error setting start URL:', response.data.result)
    } else if (window.self !== window.top) {
      window.top!.location.reload()
    } else {
      window.location.reload()
    }
  } catch (error) {
    console.error('Request failed:', error)
  }
}

const isKioskMode = kioskMode.isActive()
const navigationToggleIcon = isKioskMode ? 'toggle-off' : 'toggle-on'
const navigationToggleLink = computed(() => {
  if (!props.selectedDashboard) {
    return '' // dropdown is disabled when no dashboard is selected, so this doesn't matter
  }
  const dashboardUrl = urlHandler.getDashboardUrl(props.selectedDashboard, props.runtimeFilters)
  return kioskMode.toggled(dashboardUrl).toString()
})

const isBuiltInDashboard = computed(
  () => props.selectedDashboard?.type === DashboardOwnerType.BUILT_IN
)

const isInteractionDisabled = computed(() => props.isDashboardLoading || !props.selectedDashboard)

const sharingState = computed((): SharingState => {
  if (!props.publicToken) {
    return 'disabled'
  }
  return props.publicToken.is_disabled ? 'paused' : 'active'
})

const copyInternalDashboardLink = async (): Promise<void> => {
  const url = window?.parent?.location?.href || window.location.href
  await copyToClipboard(url)
}

// Matches the header's container width; the picker's flyout still offers the presets
const PRESETS_HIDDEN_BREAKPOINT = 821
const headerRef = ref<HTMLElement | null>(null)
const headerWidth = ref(Number.POSITIVE_INFINITY)
useResizeObserver(([entry]) => {
  if (entry) {
    headerWidth.value = entry.contentRect.width
  }
}).observe(headerRef)
const timePickerVariant = computed(() =>
  headerWidth.value < PRESETS_HIDDEN_BREAKPOINT ? 'minimal' : 'condensed'
)
</script>

<template>
  <div ref="headerRef" class="db-menu-header">
    <div class="db-menu-header__bar" role="toolbar" :aria-label="_t('Dashboard menu')">
      <div class="db-menu-header__left">
        <div class="db-menu-header__title">
          <DrillUpButton v-if="props.drillUp" v-bind="props.drillUp" />
          <CmkHeading>{{ _t('Dashboard') }}</CmkHeading>
        </div>
        <DashboardSelector
          :selected-dashboard="props.selectedDashboard"
          :disabled="props.isDashboardLoading || props.isEditMode"
          @dashboard-change="handleDashboardChange"
        />
      </div>
      <div class="db-menu-header__center">
        <template v-if="!isEditMode">
          <GlobalTimePicker
            v-model="range"
            class="db-menu-header__time-picker"
            :custom-time-ranges="props.globalTimePicker.custom_time_ranges"
            :server-time-zone="props.globalTimePicker.server_time_zone"
            :first-day-of-week="props.globalTimePicker.first_day_of_week"
            :disabled="isInteractionDisabled"
            :variant="timePickerVariant"
          >
            <template #trailing>
              <div class="db-menu-header__filter">
                <div class="db-menu-header__separator db-menu-header__filter-separator" />
                <MenuButton :disabled="isInteractionDisabled" @click="emit('open-runtime-filter')">
                  <CmkIcon name="filter" size="large" />
                  <span class="db-menu-header__button-label">{{ _t('Filter') }}</span>
                </MenuButton>
              </div>
            </template>
          </GlobalTimePicker>
        </template>
      </div>
      <div class="db-menu-header__right">
        <template v-if="!isEditMode">
          <SharingStatus
            v-if="canEditDashboard && !isBuiltInDashboard"
            class="db-menu-header__sharing-status"
            :sharing-state="sharingState"
            :shared-until="publicToken?.expires_at ? new Date(publicToken?.expires_at) : null"
            @open-sharing-settings="emit('open-share-workflow')"
          />

          <!-- vue-tsc reads a kebab-case `aria-label` as an HTML attribute rather than the
             `ariaLabel` prop, so it could not check that the icon-only dropdowns have a name. -->
          <!-- eslint-disable vue/attribute-hyphenation -->
          <DropdownMenu
            :icon="{ name: 'share', primaryColor: '--interactive-accent-strong' }"
            :ariaLabel="_t('Share')"
            :right="!(isBuiltInDashboard || canEditDashboard)"
            :disabled="isInteractionDisabled"
            :options="[
              { label: _t('Copy internal link'), action: copyInternalDashboardLink },
              {
                label: _t('Copy public link'),
                hidden: isBuiltInDashboard || !canEditDashboard || !publicToken,
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
            :ariaLabel="_t('Settings')"
            :right="true"
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
                label: _t('Clone as responsive dashboard'),
                action: () => emit('open-responsive-clone-workflow'),
                hidden: !canCloneAsResponsive
              },
              {
                label: _t('Dashboard user guide'),
                url: linkUserGuide,
                target: '_blank',
                icon: 'external'
              },
              { label: _t('Set as start URL'), action: () => setStartUrl() },
              {
                label: _t('Show page navigation'),
                url: navigationToggleLink,
                icon: navigationToggleIcon
              }
            ]"
          />
          <!-- eslint-enable vue/attribute-hyphenation -->

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
            <span class="db-menu-header__button-label">{{
              isEmptyDashboard ? _t('Add widget') : _t('Edit widgets')
            }}</span>
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

            <div class="db-menu-header__separator" />

            <MenuButton :disabled="isInteractionDisabled" @click="handleAddWidget">
              <CmkIcon name="plus" />
              {{ _t('Add widget') }}
            </MenuButton>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
/* The header adapts to the dashboard's width, not the viewport's */
.db-menu-header {
  --db-selector-max-width: 250px;

  container-type: inline-size;
}

.db-menu-header__bar {
  display: flex;
  flex-flow: row nowrap;
  align-items: stretch;
  gap: var(--dimension-10);
  background-color: transparent;
  transition: gap 0.2s ease;
}

/* Collapsible without leaving the accessibility tree; the cap fits translated labels */
.db-menu-header__button-label {
  max-width: 200px;
  overflow: hidden;
  white-space: nowrap;
  transition:
    max-width 0.2s ease,
    opacity 0.2s ease,
    margin-left 0.2s ease;
}

/*
 * Shrinks linearly from 288px outer width at 1000px header width to 110px at 821px.
 * Content widths exclude the selector's 38px horizontal padding and border.
 */
.db-menu-header__left :deep(.dashboard-selector) {
  min-width: 0;
  width: clamp(
    72px,
    100cqi - calc(1000px - var(--db-selector-max-width)),
    var(--db-selector-max-width)
  );
}

.db-menu-header__title {
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
}

.db-menu-header__left {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: flex-start;
  gap: var(--dimension-4);
  padding-bottom: var(--dimension-7);
  flex: 0 0 auto;
}

.db-menu-header__center {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  flex: 1 0 auto;
  min-width: 0;
  min-height: 96px;
}

.db-menu-header__right {
  display: flex;
  align-items: center;
  padding-top: var(--dimension-8);
  gap: var(--dimension-4);
  flex: 0 0 auto;
}

.db-menu-header__time-picker {
  flex: 1 1 auto;
  min-width: 0;
}

/* Fades and collapses before display: none applies, and back in from @starting-style */
.db-menu-header__sharing-status {
  max-width: 400px;
  overflow: hidden;
  transition:
    opacity 0.2s ease,
    max-width 0.2s ease,
    display 0.2s allow-discrete;

  @starting-style {
    opacity: 0;
    max-width: 0;
  }
}

.db-menu-header__filter {
  display: flex;
  align-items: center;
}

.db-menu-header__separator {
  flex-shrink: 0;
  align-self: stretch;
  margin: 0 var(--dimension-2);
  border-left: var(--dimension-1) solid var(--color-mid-grey-60);
}

.db-menu-header__filter-separator {
  margin-left: var(--dimension-3);
  margin-right: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.no-underline {
  text-decoration: none !important;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.edit-mode-actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

/* Header width of 1190px and below */
@container (width <= 1190px) {
  .db-menu-header__bar {
    gap: var(--dimension-8);
  }

  /* Still named for assistive technology; the margin cancels MenuButton's 6px gap */
  .db-menu-header__button-label {
    max-width: 0;
    opacity: 0;
    margin-left: -6px;
  }

  /* Keeps the dashboard list readable under the narrowed selector */
  .db-menu-header__left :deep(.dropdown-menu) {
    right: auto;
    min-width: var(--db-selector-max-width);
  }

  .db-menu-header__right :deep(.db-status-message__container) {
    flex-direction: column;
    align-items: flex-end;
    text-align: right;
  }
}

/* Header width of 825px and below */
@container (width <= 825px) {
  .db-menu-header__bar {
    gap: var(--dimension-5);
  }
}

/* Header width of 704px and below */
@container (width <= 704px) {
  .db-menu-header__sharing-status {
    display: none;
    opacity: 0;
    max-width: 0;
  }
}
</style>
