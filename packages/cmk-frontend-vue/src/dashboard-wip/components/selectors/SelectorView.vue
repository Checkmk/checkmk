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

import { useViewsCollection } from '@/dashboard-wip/composables/api/useViewsCollection'

defineProps<{ readOnly: boolean }>()
const selectedView = defineModel<string | null>('selectedView', { required: true })

const { _t } = usei18n()
const { list, ensureLoaded, isLoading, error } = useViewsCollection()

onMounted(async () => {
  await ensureLoaded()
})

const options = computed<Array<Suggestion>>(() =>
  (list.value ?? []).map((view) => ({
    name: view.id!,
    title: untranslated(view.title!)
  }))
)
</script>

<template>
  <div>
    <div v-if="isLoading" class="loading-indicator">
      {{ _t('Loading views...') }}
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <CmkDropdown
      v-if="!isLoading && !error"
      v-model:selected-option="selectedView"
      :options="{ type: 'fixed', suggestions: options }"
      :label="_t('Select view')"
      :input-hint="_t('Choose from available views')"
      :disabled="readOnly"
      width="wide"
    />
  </div>
</template>
