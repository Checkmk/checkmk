<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import { CmkFetchError } from '@/lib/cmkFetch'
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { DualListElement } from '@/components/CmkDualList'
import CmkDualList from '@/components/CmkDualList/CmkDualList.vue'
import CmkToggleButtonGroup from '@/components/CmkToggleButtonGroup.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

import { type DashboardShare } from '@/dashboard/types/shared'

import { getContactGroups, getSites } from '../api'

const { _t } = usei18n()

interface AccessSettingsProps {
  errors: TranslatedString[]
}

defineProps<AccessSettingsProps>()

const share = defineModel<DashboardShare>('share', { required: true })

type ShareType = 'with_sites' | 'with_contact_groups' | 'with_all_users' | 'no'

const isLoading = ref<boolean>(false)
const availableElements = ref<DualListElement[]>([])
const selectedContactGroups = ref<string[]>([])
const selectedSites = ref<string[]>([])

const isContactGroupOptionDisabled = ref<boolean>(false)
let cg: DualListElement[] = []
try {
  cg = await getContactGroups()
} catch (e) {
  if (!(e instanceof CmkFetchError && e.statusCode === 403)) {
    throw e
  }
}
isContactGroupOptionDisabled.value = cg.length === 0

if (share.value !== 'no' && share.value.type === 'with_contact_groups') {
  selectedContactGroups.value = share.value.contact_groups
}

if (share.value !== 'no' && share.value.type === 'with_sites') {
  selectedSites.value = share.value.sites
}

const selectedElements = computed({
  get(): DualListElement[] {
    if (share.value === 'no' || share.value.type === 'with_all_users') {
      return []
    }

    if (shareMode.value === 'with_contact_groups') {
      return availableElements.value.filter((el) => selectedContactGroups.value.includes(el.name))
    }

    return availableElements.value.filter((el) => selectedSites.value.includes(el.name))
  },

  set(newSelected: DualListElement[]) {
    if (shareMode.value === 'with_contact_groups') {
      selectedContactGroups.value = newSelected.map((el) => el.name)
      share.value = {
        type: 'with_contact_groups',
        contact_groups: selectedContactGroups.value
      }
    } else if (shareMode.value === 'with_sites') {
      selectedSites.value = newSelected.map((el) => el.name)
      share.value = { type: 'with_sites', sites: selectedSites.value }
    }
  }
})

const loadAvailableElements = async (shareMode: ShareType) => {
  const fetchers: Record<string, () => Promise<DualListElement[]>> = {
    with_contact_groups: getContactGroups,
    with_sites: getSites
  }

  const fetchData = fetchers[shareMode]
  if (!fetchData) {
    return
  }

  isLoading.value = true
  try {
    availableElements.value = await fetchData()
  } catch (e) {
    if (!(e instanceof CmkFetchError && e.statusCode === 403)) {
      throw e
    }
    availableElements.value = []
  } finally {
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
        share.value = { type: 'with_sites', sites: selectedSites.value }
        void loadAvailableElements('with_sites')
        break

      case 'with_contact_groups':
        share.value = { type: 'with_contact_groups', contact_groups: selectedContactGroups.value }
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
  <CmkToggleButtonGroup
    v-model="shareMode"
    :options="[
      { label: _t('Only me (private)'), value: 'no' },
      { label: _t('All users'), value: 'with_all_users' },
      {
        label: _t('Members of contact groups'),
        value: 'with_contact_groups',
        disabled: isContactGroupOptionDisabled,
        disabledTooltip: _t('No contact groups found')
      },
      { label: _t('Users of site'), value: 'with_sites' }
    ]"
  />

  <CmkInlineValidation v-if="displayDualList && errors.length > 0" :validation="errors" />
  <CmkDualList
    v-if="displayDualList"
    v-model:data="selectedElements"
    :elements="availableElements"
    :title="_t('Visual information')"
    :validators="[]"
    :backend-validation="[]"
  />
</template>
