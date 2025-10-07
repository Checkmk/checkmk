<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'

import usei18n from '@/lib/i18n'

import type { DualListElement } from '@/components/CmkDualList'
import CmkDualList from '@/components/CmkDualList/CmkDualList.vue'

import { useVisualInfoCollection } from '@/dashboard-wip/composables/api/useVisualInfoCollection'

const props = defineProps<{
  onlyIds?: string[] | null
}>()

const selectedIds = defineModel<string[]>('selectedIds', { required: true })

const { _t } = usei18n()
const { ensureLoaded, list, isLoading, error } = useVisualInfoCollection()

onMounted(async () => {
  await ensureLoaded()
})

const allElements = computed<DualListElement[]>(() => {
  const els: DualListElement[] = []
  for (const visualInfo of list.value) {
    els.push({ name: visualInfo.id!, title: `Show information of a single ${visualInfo.title!}` })
  }
  return els
})

const allowedIds = computed<Set<string> | null>(() => {
  return props.onlyIds?.length ? new Set(props.onlyIds) : null
})

const filteredElements = computed<DualListElement[]>(() => {
  if (!allowedIds.value) {
    return allElements.value
  }
  return allElements.value.filter((e) => allowedIds.value!.has(e.name))
})

const dataElements = computed<DualListElement[]>({
  get() {
    const ids = selectedIds.value || []
    const effective = allowedIds.value ? ids.filter((id) => allowedIds.value!.has(id)) : ids

    return effective.map((id) => {
      const found = filteredElements.value.find((e) => e.name === id)
      const baseTitle = found!.title!
      return { name: id, title: `Show information of a single ${baseTitle}` }
    })
  },
  set(newEls) {
    selectedIds.value = newEls.map((e) => e.name)
  }
})

watch(allowedIds, () => {
  if (!allowedIds.value) {
    return
  }
  selectedIds.value = (selectedIds.value || []).filter((id) => allowedIds.value!.has(id))
})
</script>

<template>
  <div class="vi-selector">
    <div class="vi-selector__meta">
      <span v-if="isLoading">{{ _t('Loading…') }}</span>
      <span v-else-if="error" class="error">
        {{ _t('Failed to load options') }} — {{ error }}
      </span>
    </div>

    <CmkDualList
      v-if="!isLoading"
      v-model:data="dataElements"
      :elements="filteredElements"
      :title="_t('Visual information')"
      :validators="[]"
      :backend-validation="[]"
    />

    <div v-else class="vi-selector__skeleton" aria-busy="true" aria-live="polite">
      {{ _t('Loading options…') }}
    </div>
  </div>
</template>
