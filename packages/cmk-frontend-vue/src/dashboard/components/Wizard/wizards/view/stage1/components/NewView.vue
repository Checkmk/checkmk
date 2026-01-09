<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'

import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import SingleInfosSpecifier from '@/dashboard/components/Wizard/wizards/view/stage1/components/SingleInfosSpecifier.vue'
import SelectorDatasource from '@/dashboard/components/selectors/SelectorDatasource.vue'
import type { DataSourceModel } from '@/dashboard/types/api'
import { RestrictedToSingle } from '@/dashboard/types/shared.ts'

const { _t } = usei18n()

const props = defineProps<{
  datasourcesById: Record<string, DataSourceModel>
}>()

const selectedDatasource = defineModel<string | null>('selectedDatasource', { default: null })
const contextInfos = defineModel<string[]>('contextInfos', { default: [] })
const restrictedToSingleInfos = defineModel<string[]>('restrictedToSingleInfos', { default: [] })
const singleInfosMode = ref<RestrictedToSingle>(RestrictedToSingle.NO)

watch(
  () => selectedDatasource.value,
  (id) => {
    let newInfos: string[] = []
    if (id) {
      const datasource = props.datasourcesById[id]
      newInfos = datasource?.extensions?.infos ?? []
    }

    // Only update if the content has changed to prevent resetting active filters in StageContents
    const currentInfos = contextInfos.value
    const hasChanged =
      newInfos.length !== currentInfos.length || newInfos.some((v, i) => v !== currentInfos[i])

    if (hasChanged) {
      contextInfos.value = newInfos
    }
  },
  { immediate: true }
)
</script>

<template>
  <CmkIndent>
    <h2>{{ _t('Datasource') }}</h2>
    <ContentSpacer :dimension="5" />
    <SelectorDatasource v-model:selected-datasource="selectedDatasource" :read-only="false" />
    <ContentSpacer :dimension="5" />
    <SingleInfosSpecifier
      v-model:context-infos="contextInfos"
      v-model:restricted-ids="restrictedToSingleInfos"
      v-model:mode="singleInfosMode"
    />
  </CmkIndent>
</template>
