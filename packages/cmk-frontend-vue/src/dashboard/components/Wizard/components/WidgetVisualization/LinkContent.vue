<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref, watch } from 'vue'

import SelectorView from '@/dashboard/components/selectors/SelectorView.vue'
import { type VisualCopy, useCopyOptions } from '@/dashboard/components/selectors/visualKey'

import { type DashboardTarget, fetchDashboardTargets } from './api'

const { _t } = usei18n()

interface LinkContentProps {
  linkValidation: TranslatedString[]
}
const props = defineProps<LinkContentProps>()
const linkType = defineModel<string | null>('linkType', { required: true, default: null })
const linkTarget = defineModel<VisualCopy | null>('linkTarget', { required: true })

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
const dashboards = ref<DashboardTarget[]>([])

watch(
  linkType,
  async (newLinkType: string | null) => {
    if (newLinkType === 'dashboards') {
      dashboards.value = await fetchDashboardTargets()
    } else {
      dashboards.value = []
    }
  },
  { immediate: true }
)

const { suggestions: dashboardTargets, key: dashboardKey } = useCopyOptions(linkTarget, () =>
  dashboards.value.map((dashboard) => ({
    copy: { name: dashboard.name, owner: dashboard.owner },
    title: untranslated(
      dashboard.owner === '' ? dashboard.title : `${dashboard.title} (${dashboard.owner})`
    )
  }))
)
</script>

<template>
  <CmkCheckbox v-model="linkEnabled" :label="_t('Link content to')" />
  <CmkIndent v-if="linkEnabled">
    <div class="db-link-content__container">
      <div class="db-link-content__item">
        <CmkDropdown
          v-model="linkType"
          :label="_t('Select a category')"
          :options="{ type: 'fixed', suggestions: linkOptions }"
        />
      </div>
      <div class="db-link-content__item">
        <CmkDropdown
          v-if="linkType === 'dashboards'"
          v-model="dashboardKey"
          :label="_t('Select a target')"
          :options="{ type: 'filtered', suggestions: dashboardTargets }"
        />
        <SelectorView
          v-else
          v-model:selected-copy="linkTarget"
          :read-only="false"
          width="fill"
          by-owner
        />
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
