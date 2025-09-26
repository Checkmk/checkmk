<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import type { DualListElement } from '@/components/CmkDualList'
import CmkDualList from '@/components/CmkDualList/CmkDualList.vue'
import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'

import { type DashboardShare } from '@/dashboard-wip/types/shared'

import { getContactGroups, getSites } from '../api'

const { _t } = usei18n()

const share = defineModel<DashboardShare>('share', { required: true })

type ShareType = 'with_sites' | 'with_contact_groups' | 'with_all_users' | 'no'

const isLoading = ref<boolean>(false)
const availableElements = ref<DualListElement[]>([])

const _getSelectedNames = (): string[] => {
  if (share.value === 'no' || share.value.type === 'with_all_users') {
    return []
  }

  if (share.value.type === 'with_contact_groups') {
    return share.value.contact_groups
  }

  return share.value.sites
}

const selectedElements = computed({
  get(): DualListElement[] {
    if (share.value === 'no' || share.value.type === 'with_all_users') {
      return []
    }

    if (shareMode.value === 'with_contact_groups') {
      return availableElements.value.filter((el) => _getSelectedNames().includes(el.name))
    }

    return availableElements.value.filter((el) => _getSelectedNames().includes(el.name))
  },

  set(newSelected: DualListElement[]) {
    if (shareMode.value === 'with_contact_groups') {
      share.value = {
        type: 'with_contact_groups',
        contact_groups: newSelected.map((el) => el.name)
      }
    } else if (shareMode.value === 'with_sites') {
      share.value = { type: 'with_sites', sites: newSelected.map((el) => el.name) }
    }
  }
})

const loadAvailableElements = async (shareMode: ShareType) => {
  if (shareMode === 'with_contact_groups') {
    isLoading.value = true
    availableElements.value = await getContactGroups()
    isLoading.value = false
  } else if (shareMode === 'with_sites') {
    isLoading.value = true
    availableElements.value = await getSites()
    isLoading.value = false
  }
}

const shareMode = computed({
  get(): string {
    if (share.value === 'no') {
      return 'no'
    } else {
      return share.value.type
    }
  },

  set(newMode: string) {
    switch (newMode) {
      case 'with_sites':
        share.value = { type: 'with_sites', sites: [] }
        void loadAvailableElements('with_sites')
        break

      case 'with_contact_groups':
        share.value = { type: 'with_contact_groups', contact_groups: [] }
        void loadAvailableElements('with_contact_groups')
        break

      case 'with_all_users':
        share.value = { type: 'with_all_users' }
        availableElements.value = []
        break

      default:
        share.value = 'no'
        availableElements.value = []
        break
    }
  }
})

const displayDualList = computed((): boolean => {
  return !isLoading.value && ['with_contact_groups', 'with_sites'].includes(shareMode.value)
})

if (shareMode.value === 'with_contact_groups' || shareMode.value === 'with_sites') {
  await loadAvailableElements(shareMode.value as ShareType)
}
</script>

<template>
  <ToggleButtonGroup
    v-model="shareMode"
    :options="[
      { label: _t('Only me (private)'), value: 'no' },
      { label: _t('All users'), value: 'with_all_users' },
      { label: _t('Members of contact groups'), value: 'with_contact_groups' },
      { label: _t('Users of site'), value: 'with_sites' }
    ]"
  />

  <CmkDualList
    v-if="displayDualList"
    v-model:data="selectedElements"
    :elements="availableElements"
    :title="_t('Visual information')"
    :validators="[]"
    :backend-validation="[]"
  />
</template>
