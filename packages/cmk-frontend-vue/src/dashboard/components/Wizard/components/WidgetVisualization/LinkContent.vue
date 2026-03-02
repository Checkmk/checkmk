<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import type { Suggestion } from '@/components/CmkSuggestions'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

import SelectorView from '@/dashboard/components/selectors/SelectorView.vue'

import { fetchDashboards } from './api'

const { _t } = usei18n()

interface LinkContentProps {
  linkValidation: TranslatedString[]
}
const props = defineProps<LinkContentProps>()
const linkType = defineModel<string | null>('linkType', { required: true, default: null })
const linkTarget = defineModel<string | null>('linkTarget', { required: true })

const linkOptions = computed(() => [
  { name: 'dashboards', title: _t('Dashboards') },
  { name: 'views', title: _t('Views') }
])

const linkEnabled = computed({
  get: () => linkType.value !== null,
  set: (value: boolean) => {
    linkType.value = value ? linkOptions.value[0]!.name : null
  }
})

const isError = computed(() => props.linkValidation.length > 0)
const dashboardTargets = ref<Suggestion[]>([])

watch(linkType, async (newLinkType: string | null) => {
  if (newLinkType === 'dashboards') {
    dashboardTargets.value = await fetchDashboards()
  } else {
    dashboardTargets.value = []
  }
})
</script>

<template>
  <CmkCheckbox v-model="linkEnabled" :label="_t('Link content to')" />
  <CmkIndent v-if="linkEnabled">
    <div class="db-link-content__container">
      <div class="db-link-content__item">
        <CmkDropdown
          v-model:selected-option="linkType"
          :label="_t('Select a category')"
          :options="{ type: 'fixed', suggestions: linkOptions }"
        />
      </div>
      <div class="db-link-content__item">
        <CmkDropdown
          v-if="linkType === 'dashboards'"
          v-model:selected-option="linkTarget"
          :label="_t('Select a target')"
          :options="{ type: 'filtered', suggestions: dashboardTargets }"
        />
        <SelectorView v-else v-model:selected-view="linkTarget" :read-only="false" width="fill" />
      </div>
    </div>
    <div v-if="isError">
      <CmkInlineValidation :validation="linkValidation" />
    </div>
  </CmkIndent>
</template>

<style scoped>
.db-link-content__container {
  display: inline-grid;
  grid-template-columns: auto minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  gap: 0 var(--dimension-6);
}

.db-link-content__item:first-child {
  grid-area: 1 / 1 / 2 / 2;
}

.db-link-content__item:last-child {
  grid-area: 1 / 2 / 2 / 3;
}
</style>
