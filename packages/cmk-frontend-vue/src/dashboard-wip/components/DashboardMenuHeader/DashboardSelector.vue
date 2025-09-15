<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

import usei18n from '@/lib/i18n.ts'

import CmkLabel from '@/components/CmkLabel.vue'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'

import type { DashboardMetadata } from '@/dashboard-wip/types/dashboard.ts'
import { dashboardAPI } from '@/dashboard-wip/utils.ts'

import type { SelectedDashboard } from './types.ts'

const { _t } = usei18n()

interface Props {
  selectedDashboard: SelectedDashboard | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'dashboard-change': [dashboard: DashboardMetadata]
}>()

const showDashboardDropdown = ref(false)
const dropdownRef = ref<HTMLElement>()
const inputRef = ref<HTMLInputElement>()
const inputValue = ref('')
const dashboards = ref<DashboardMetadata[]>([])
const isLoading = ref(false)

const filteredDashboards = computed(() => {
  if (!inputValue.value.trim()) {
    return dashboards.value.filter((dashboard) => dashboard?.display.title)
  }

  const filterText = inputValue.value.toLowerCase().trim()
  return dashboards.value.filter((dashboard) =>
    dashboard?.display.title.toLowerCase().includes(filterText)
  )
})

const groupedDashboards = computed(() => {
  const filtered = filteredDashboards.value

  const customDashboards = filtered
    .filter((d) => !d?.is_built_in)
    .sort((a, b) => (a?.display.title || '').localeCompare(b?.display.title || ''))

  const builtInDashboards = filtered
    .filter((d) => d?.is_built_in)
    .sort((a, b) => {
      const sortA = a?.display.sort_index || 0
      const sortB = b?.display.sort_index || 0
      const titleA = a?.display.title || ''
      const titleB = b?.display.title || ''
      return sortA - sortB || titleA.localeCompare(titleB)
    })

  return {
    custom: customDashboards,
    builtIn: builtInDashboards
  }
})

const fetchDashboards = async () => {
  isLoading.value = true
  const result = await dashboardAPI.listDashboardMetadata()
  dashboards.value = result || []
  isLoading.value = false
}

const handleInputFocus = () => {
  inputValue.value = ''
  showDashboardDropdown.value = true
  void fetchDashboards()
}

const handleInputBlur = () => {
  // Delay hiding dropdown to allow for clicks on dropdown items
  setTimeout(() => {
    showDashboardDropdown.value = false
    inputValue.value = props.selectedDashboard?.title || ''
  }, 150)
}

const handleDashboardSelect = (dashboard: DashboardMetadata) => {
  if (!dashboard?.display?.title) {
    console.warn('Dashboard selected without valid title:', dashboard)
    return
  }

  emit('dashboard-change', dashboard)
  inputValue.value = dashboard.display.title
  showDashboardDropdown.value = false
  inputRef.value?.blur()
}

const handleClickOutside = (event: Event) => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    showDashboardDropdown.value = false
    inputValue.value = props.selectedDashboard?.title || ''
  }
}

watch(
  () => props.selectedDashboard,
  (newValue) => {
    if (!showDashboardDropdown.value) {
      inputValue.value = newValue?.title || ''
    }
  },
  { immediate: true }
)

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  inputValue.value = props.selectedDashboard?.title || ''
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div
    ref="dropdownRef"
    class="dashboard-dropdown"
    :class="{ 'dropdown-open': showDashboardDropdown }"
  >
    <input
      ref="inputRef"
      v-model="inputValue"
      class="dashboard-selector"
      type="text"
      :placeholder="props.selectedDashboard?.title || _t('Select dashboard')"
      @focus="handleInputFocus"
      @blur="handleInputBlur"
    />

    <div v-if="showDashboardDropdown" class="dropdown-menu">
      <CmkScrollContainer max-height="300px">
        <div v-if="isLoading" class="dropdown-loading">{{ _t('Loading Dashboards') }}...</div>

        <div v-else-if="filteredDashboards.length === 0" class="dropdown-empty">
          {{ _t('No dashboards found') }}
        </div>

        <div v-else class="dropdown-content">
          <!-- Custom Dashboards -->
          <div v-if="groupedDashboards.custom.length > 0" class="dashboard-group">
            <div class="group-header">{{ _t('Custom dashboards') }}</div>
            <div
              v-for="dashboard in groupedDashboards.custom"
              :key="dashboard.name"
              class="dropdown-item"
              :class="{ active: dashboard?.display?.title === props.selectedDashboard?.title }"
              @click="handleDashboardSelect(dashboard)"
            >
              {{ dashboard?.display?.title || 'Unnamed Dashboard' }}
            </div>
          </div>

          <!-- Built-in Dashboards -->
          <div v-if="groupedDashboards.builtIn.length > 0" class="dashboard-group">
            <div class="group-header">
              {{ _t('Built-in dashboards') }}
            </div>
            <div
              v-for="dashboard in groupedDashboards.builtIn"
              :key="dashboard.name"
              class="dropdown-item"
              :class="{ active: dashboard?.display?.title === props.selectedDashboard?.title }"
              @click="handleDashboardSelect(dashboard)"
            >
              <CmkLabel>{{ dashboard?.display?.title || _t('Unnamed Dashboard') }}</CmkLabel>
            </div>
          </div>
        </div>
      </CmkScrollContainer>
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-dropdown {
  position: relative;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-selector {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: var(--ux-theme-5);
  border: var(--dimension-1) solid var(--color-mid-grey-60);
  padding: var(--dimension-4) var(--dimension-5);
  transition: all 0.2s ease;
  min-width: 250px;
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
  outline: none;
  border-radius: var(--dimension-3);
  cursor: pointer;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-selector:focus {
  color: var(--font-color);
  cursor: text;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background-color: var(--ux-theme-3);
  border-radius: var(--dimension-3);
  z-index: 1000;
  margin-top: var(--dimension-2);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dropdown-content {
  padding: var(--dimension-4) 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-group {
  margin-bottom: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-group:last-child {
  margin-bottom: 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.group-header {
  padding: var(--dimension-4) var(--dimension-6) var(--dimension-3);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dropdown-item {
  display: block;
  padding: var(--dimension-4) var(--dimension-6);
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  font-size: var(--font-size-normal);
  transition: background-color 0.2s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dropdown-item:hover {
  background-color: var(--ux-theme-5);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dropdown-item.active {
  color: #fff;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dropdown-loading,
.dropdown-empty {
  padding: var(--dimension-6);
  text-align: center;
  color: var(--font-color);
  font-size: var(--font-size-normal);
}
</style>
