<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker.ts'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time/types.ts'
import usei18n from 'cmk-ui-library/lib/i18n'
import useClickOutside from 'cmk-ui-library/lib/useClickOutside'
import { ref } from 'vue'

import DashboardRefreshControl from '@/dashboard/components/DashboardRefreshControl.vue'
import GlobalTimePicker from '@/graphing/GlobalTimePicker/GlobalTimePicker.vue'

interface Props {
  dashboardTitle: string
  globalTimePicker: GlobalTimePickerProps
}

const { _t } = usei18n()

const props = defineProps<Props>()

const range = defineModel<DateTimeRange>('range', { required: true })

const vClickOutside = useClickOutside()

const menuShown = ref(false)

const showTimePicker = ref(true)
const showRefresh = ref(true)

const toggleTimePicker = () => {
  showTimePicker.value = !showTimePicker.value
}

const toggleRefresh = () => {
  showRefresh.value = !showRefresh.value
}

const toggleMenu = () => {
  menuShown.value = !menuShown.value
}

const hideMenu = () => {
  menuShown.value = false
}
</script>

<template>
  <div class="db-shared-dashboard-menu-header__sections">
    <div class="db-shared-dashboard-menu-header__title-section">
      <div class="db-shared-dashboard-menu-header__dashboard-title">
        <CmkLabel variant="title">{{ dashboardTitle }}</CmkLabel>
      </div>
    </div>

    <div class="db-shared-dashboard-menu-header__time-range-section">
      <GlobalTimePicker
        v-if="showTimePicker"
        v-model="range"
        class="db-shared-dashboard-menu-header__time-picker"
        :custom-time-ranges="props.globalTimePicker.custom_time_ranges"
        :server-time-zone="props.globalTimePicker.server_time_zone"
        :first-day-of-week="props.globalTimePicker.first_day_of_week"
        variant="condensed"
      />
    </div>
    <div class="db-shared-dashboard-menu-header__refresh-control-section">
      <DashboardRefreshControl
        v-if="showRefresh"
        :default-time-range="props.globalTimePicker.default_time_range"
        :interval-choices-seconds="props.globalTimePicker.refresh.interval_choices_seconds"
      />
    </div>

    <div class="db-shared-dashboard-menu-header__menu-section">
      <div
        v-click-outside="{ open: menuShown, close: hideMenu }"
        class="db-shared-dashboard-menu-header__icon-dropdown-menu"
      >
        <button
          class="db-shared-dashboard-menu-header__icon-dropdown-menu-trigger"
          :class="{
            'db-shared-dashboard-menu-header__icon-dropdown-menu-trigger--open': menuShown
          }"
          :aria-label="_t('Settings Menu')"
          :aria-expanded="menuShown"
          @click="toggleMenu"
        >
          <CmkMultitoneIcon name="menu" size="medium" primary-color="font" />
        </button>

        <div
          v-if="menuShown"
          class="db-shared-dashboard-menu-header__icon-dropdown-menu--container"
        >
          <div class="db-shared-dashboard-menu-header__icon-dropdown-menu--content">
            <div class="db-shared-dashboard-menu-header__dropdown-menu-items">
              <a
                class="db-shared-dashboard-menu-header__menu-item"
                @click="
                  () => {
                    toggleTimePicker()
                    hideMenu()
                  }
                "
              >
                <div class="db-shared-dashboard-menu-header__menu-label">
                  {{ _t('Show date time picker') }}
                </div>
                <CmkIcon :name="showTimePicker ? 'toggle-on' : 'toggle-off'" />
              </a>
              <a
                class="db-shared-dashboard-menu-header__menu-item"
                @click="
                  () => {
                    toggleRefresh()
                    hideMenu()
                  }
                "
              >
                <div class="db-shared-dashboard-menu-header__menu-label">
                  {{ _t('Show live refresh') }}
                </div>
                <CmkIcon :name="showRefresh ? 'toggle-on' : 'toggle-off'" />
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.db-shared-dashboard-menu-header__sections {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: transparent;
  color: var(--font-color);
  padding: var(--dimension-4);
  font-size: var(--font-size-large);
  min-height: 36px;
  flex-wrap: wrap;
  gap: var(--dimension-4);
}

.db-shared-dashboard-menu-header__title-section {
  display: flex;
  align-items: center;
  flex: 0 1 auto;
}

.db-shared-dashboard-menu-header__time-range-section {
  display: flex;
  align-items: center;
  flex: 0 1 auto;
  min-width: 0;
}

.db-shared-dashboard-menu-header__time-picker {
  flex: 1 1 auto;
  min-width: 0;
}

.db-shared-dashboard-menu-header__refresh-control-section {
  display: flex;
  flex: 0 0 auto;
  margin-left: auto;
}

.db-shared-dashboard-menu-header__dashboard-title {
  display: flex;
  align-items: center;
}

.db-shared-dashboard-menu-header__dropdown-menu-items {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.db-shared-dashboard-menu-header__menu-item {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: var(--dimension-4) var(--dimension-5);
  border: none;
  background: none;
  color: var(--font-color);
  font-size: var(--font-size-normal);
  text-align: left;
  text-decoration: none;
  cursor: pointer;
  border-radius: var(--border-radius);
  transition: background-color 0.2s ease;
}

.db-shared-dashboard-menu-header__menu-item:hover {
  background-color: var(--ux-theme-5);
}

.db-shared-dashboard-menu-header__menu-label {
  color: var(--font-color);
  flex: 1;
}

.db-shared-dashboard-menu-header__menu-section {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  margin-left: var(--dimension-5);
}

.db-shared-dashboard-menu-header__icon-dropdown-menu {
  display: inline-block;
  position: relative;
  white-space: nowrap;
}

.db-shared-dashboard-menu-header__icon-dropdown-menu-trigger {
  box-sizing: border-box;
  height: var(--dimension-7);
  width: var(--dimension-7);
  border: 1px solid transparent;
  border-radius: var(--border-radius) var(--border-radius) 0 0;
  padding: 0 0 1px;
  margin: 0;
  background: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.2s ease;
}

.db-shared-dashboard-menu-header__icon-dropdown-menu-trigger:hover {
  opacity: 0.8;
}

.db-shared-dashboard-menu-header__icon-dropdown-menu-trigger:focus {
  outline: none;
}

.db-shared-dashboard-menu-header__icon-dropdown-menu-trigger--open {
  border-color: var(--button-form-border-color);
}

.db-shared-dashboard-menu-header__icon-dropdown-menu--container {
  position: absolute;
  right: 0;
  margin-top: -1px;
  z-index: 100;
  color: var(--font-color);
  background-color: var(--ux-theme-2);
  box-sizing: border-box;
  border: 1px solid var(--button-form-border-color);
  border-radius: 0 0 var(--border-radius) var(--border-radius);
  min-width: 200px;
  width: max-content;
}

.db-shared-dashboard-menu-header__icon-dropdown-menu--content {
  padding: var(--dimension-3);
  margin: 0;
}
</style>
