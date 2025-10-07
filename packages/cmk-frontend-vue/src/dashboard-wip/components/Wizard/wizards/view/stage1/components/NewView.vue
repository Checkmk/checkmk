<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'

import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import SingleInfosSpecifier from '@/dashboard-wip/components/Wizard/wizards/view/stage1/components/SingleInfosSpecifier.vue'
import SelectorDatasource from '@/dashboard-wip/components/selectors/SelectorDatasource.vue'
import { useDataSourcesCollection } from '@/dashboard-wip/composables/api/useDataSourcesCollection.ts'
import { RestrictedToSingle } from '@/dashboard-wip/types/shared.ts'

const { _t } = usei18n()

const selectedDatasource = defineModel<string | null>('selectedDatasource', { default: null })
const contextInfos = defineModel<string[]>('contextInfos', { default: [] })
const restrictedToSingleInfos = defineModel<string[]>('restrictedToSingleInfos', { default: [] })
const singleInfosMode = ref<RestrictedToSingle>(RestrictedToSingle.NO)

const { byId: byDatasourceId, ensureLoaded: ensureDataSourcesLoaded } = useDataSourcesCollection()

onMounted(async () => {
  await ensureDataSourcesLoaded()
})

watch(
  () => selectedDatasource.value,
  (id) => {
    if (!id) {
      contextInfos.value = []
      return
    }
    const datasource = byDatasourceId.value[id]
    contextInfos.value = datasource?.extensions?.infos ?? []
  },
  { immediate: true }
)
</script>

<template>
  <CmkIndent>
    <h2>{{ _t('Datasource') }}</h2>
    <ContentSpacer :height="10" />
    <SelectorDatasource v-model:selected-datasource="selectedDatasource" :read-only="false" />
    <ContentSpacer />
    <SingleInfosSpecifier
      v-model:context-infos="contextInfos"
      v-model:restricted-ids="restrictedToSingleInfos"
      v-model:mode="singleInfosMode"
    />
  </CmkIndent>
</template>
