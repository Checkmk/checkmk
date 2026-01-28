<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'
import useClickOutside from '@/lib/useClickOutside'

import CmkIcon from '@/components/CmkIcon'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkLabel from '@/components/CmkLabel.vue'

interface Props {
  dashboardTitle: string
}

const { _t } = usei18n()

defineProps<Props>()

const vClickOutside = useClickOutside()

// UTC time state
const currentUtcDate = ref('')
const currentUtcTime = ref('')
const showDateTime = ref(true)
let intervalId: number | null = null

const menuShown = ref(false)

const updateUtcTime = () => {
  const now = new Date()
  const day = now.getUTCDate().toString().padStart(2, '0')
  const month = (now.getUTCMonth() + 1).toString().padStart(2, '0')
  const year = now.getUTCFullYear()
  currentUtcDate.value = `${day}-${month}-${year}`

  const hours = now.getUTCHours().toString().padStart(2, '0')
  const minutes = now.getUTCMinutes().toString().padStart(2, '0')
  currentUtcTime.value = `${hours}:${minutes}`
}

const toggleDateTime = () => {
  showDateTime.value = !showDateTime.value
}

const toggleMenu = () => {
  menuShown.value = !menuShown.value
  if (!menuShown.value) {
    return
  }
}

const hideMenu = () => {
  menuShown.value = false
}

onMounted(() => {
  updateUtcTime()
  intervalId = window.setInterval(updateUtcTime, 1000)
})

onUnmounted(() => {
  if (intervalId !== null) {
    clearInterval(intervalId)
  }
})
</script>

<template>
  <div class="db-shared-dashboard-menu-header__sections">
    <div class="db-shared-dashboard-menu-header__left-section">
      <div class="db-shared-dashboard-menu-header__dashboard-title">
        <CmkLabel variant="title">{{ dashboardTitle }}</CmkLabel>
      </div>
    </div>

    <div class="db-shared-dashboard-menu-header__right-section">
      <div v-if="showDateTime" class="db-shared-dashboard-menu-header__utc-time">
        <span class="db-shared-dashboard-menu-header__utc-date">{{ currentUtcDate }}</span>
        <span class="db-shared-dashboard-menu-header__utc-time-only"
          >{{ currentUtcTime }} {{ untranslated('UTC') }}</span
        >
      </div>

      <div
        v-click-outside="
          () => {
            menuShown = false
          }
        "
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
                    toggleDateTime()
                    hideMenu()
                  }
                "
              >
                <div class="db-shared-dashboard-menu-header__menu-label">
                  {{ _t('Show date and time') }}
                </div>
                <CmkIcon :name="showDateTime ? 'toggle-on' : 'toggle-off'" />
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
}

.db-shared-dashboard-menu-header__left-section {
  display: flex;
  align-items: center;
  gap: var(--dimension-6);
  flex: 1;
}

.db-shared-dashboard-menu-header__dashboard-title {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.db-shared-dashboard-menu-header__utc-time {
  color: var(--font-color);
  font-size: var(--font-size-normal);
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
}

.db-shared-dashboard-menu-header__utc-date {
  font-weight: var(--font-weight-bold);
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
  border-radius: var(--dimension-3);
  transition: background-color 0.2s ease;
}

.db-shared-dashboard-menu-header__menu-item:hover {
  background-color: var(--ux-theme-5);
}

.db-shared-dashboard-menu-header__menu-label {
  color: var(--font-color);
  flex: 1;
}

.db-shared-dashboard-menu-header__right-section {
  display: flex;
  align-items: center;
  gap: var(--dimension-5);
  flex: 1;
  justify-content: flex-end;
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
  border-radius: var(--border-radius-half) var(--border-radius-half) 0 0;
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
