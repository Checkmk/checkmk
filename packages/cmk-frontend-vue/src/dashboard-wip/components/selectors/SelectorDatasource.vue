<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown.vue'
import type { Suggestion } from '@/components/suggestions'

import { useDataSourcesCollection } from '@/dashboard-wip/composables/api/useDataSourcesCollection'

defineProps<{ readOnly: boolean }>()
const selectedDatasource = defineModel<string | null>('selectedDatasource', { required: true })

const { _t } = usei18n()
const { list, ensureLoaded, isLoading, error } = useDataSourcesCollection()

onMounted(async () => {
  await ensureLoaded()
})

const options = computed<Array<Suggestion>>(() =>
  (list.value ?? []).map((ds) => ({
    name: ds.id!,
    title: untranslated(ds.title!)
  }))
)
</script>

<template>
  <div>
    <div v-if="isLoading" class="loading-indicator">
      {{ _t('Loading datasources...') }}
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <CmkDropdown
      v-if="!isLoading && !error"
      v-model:selected-option="selectedDatasource"
      :options="{ type: 'fixed', suggestions: options }"
      :label="_t('Select datasource')"
      :input-hint="_t('Choose from available datasources')"
      :disabled="readOnly"
      width="wide"
    />
  </div>
</template>
