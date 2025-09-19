<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchRestAPI } from '@/lib/cmkFetch.ts'
import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import type { DualListElement } from '@/components/CmkDualList'
import CmkDualList from '@/components/CmkDualList/CmkDualList.vue'

import type { VisualInfoCollectionModel } from '@/dashboard-wip/types/api.ts'

const API_ROOT = 'api/internal'

const selectedIds = defineModel<string[]>('selectedIds', { required: true })

const allElements = ref<DualListElement[]>([])
const loading = ref<boolean>(false)
const loadError = ref<string | null>(null)

const { _t } = usei18n()

async function loadCollections() {
  loading.value = true
  loadError.value = null
  try {
    const url = `${API_ROOT}/objects/constant/visual_info/collections/all`
    const resp = await fetchRestAPI(url, 'GET')
    const collection: VisualInfoCollectionModel = await resp.json()

    const list: (DualListElement & { sortIndex: number })[] = []

    for (const vi of collection?.value ?? []) {
      const id = vi.id?.trim()
      if (!id) {
        continue
      }
      const title = vi.title?.trim() || id
      const sortIndex = Number(vi.extensions?.sort_index ?? Number.MAX_SAFE_INTEGER)
      list.push({ name: id, title, sortIndex })
    }

    list.sort(
      (a, b) => (a.sortIndex ?? Number.MAX_SAFE_INTEGER) - (b.sortIndex ?? Number.MAX_SAFE_INTEGER)
    )

    allElements.value = list.map(({ name, title }) => ({
      name,
      title: `Show information of a single ${title}`
    }))
  } catch (err) {
    loadError.value = String(err)
    allElements.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadCollections)

const dataElements = computed<DualListElement[]>({
  get() {
    return (selectedIds.value || []).map((id) => {
      const found = allElements.value.find((e) => e.name === id)
      const baseTitle = found?.title?.trim() || id
      return { name: id, title: `Show information of a single ${baseTitle}` }
    })
  },
  set(newEls) {
    selectedIds.value = newEls.map((e) => e.name)
  }
})
</script>

<template>
  <div class="vi-selector">
    <div class="vi-selector__meta">
      <span v-if="loading">{{ _t('Loading…') }}</span>
      <span v-else-if="loadError" class="error">
        {{ _t('Failed to load options') }} — {{ loadError }}
      </span>
      <CmkButton v-else @click="loadCollections">{{ _t('Refresh') }}</CmkButton>
    </div>

    <CmkDualList
      v-if="!loading"
      v-model:data="dataElements"
      :elements="allElements"
      :title="_t('Visual information')"
      :validators="[]"
      :backend-validation="[]"
    />

    <div v-else class="vi-selector__skeleton" aria-busy="true" aria-live="polite">
      {{ _t('Loading options…') }}
    </div>
  </div>
</template>
