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
import SelectorView from '@/dashboard-wip/components/selectors/SelectorView.vue'
import { useDataSourcesCollection } from '@/dashboard-wip/composables/api/useDataSourcesCollection.ts'
import { useViewsCollection } from '@/dashboard-wip/composables/api/useViewsCollection.ts'
import { RestrictedToSingle } from '@/dashboard-wip/types/shared.ts'

const { _t } = usei18n()

const referencedView = defineModel<string | null>('referencedView', { default: null })
const contextInfos = defineModel<string[]>('contextInfos', { default: [] })
const restrictedToSingleInfos = defineModel<string[]>('restrictedToSingleInfos', { default: [] })
const singleInfosMode = ref<RestrictedToSingle>(RestrictedToSingle.NO)

const { byId: byViewId, ensureLoaded: ensureViewsLoaded } = useViewsCollection()
const { byId: byDatasourceId, ensureLoaded: ensureDataSourcesLoaded } = useDataSourcesCollection()

onMounted(async () => {
  await ensureDataSourcesLoaded()
  await ensureViewsLoaded()
})

watch(
  () => referencedView.value,
  (id) => {
    if (!id) {
      contextInfos.value = []
      return
    }

    const view = byViewId.value[id]
    const datasource = byDatasourceId.value[view!.extensions!.data_source]

    contextInfos.value = datasource!.extensions.infos
    const restrictedToSingle = view!.extensions?.restricted_to_single ?? []

    if (restrictedToSingle.length === 1 && restrictedToSingle[0] === 'host') {
      singleInfosMode.value = RestrictedToSingle.HOST
    } else if (restrictedToSingle.length > 0) {
      singleInfosMode.value = RestrictedToSingle.CUSTOM
    } else {
      singleInfosMode.value = RestrictedToSingle.NO
    }
    restrictedToSingleInfos.value = restrictedToSingle
  },
  { immediate: true }
)
// TODO: read-only mode for SelectorSingleInfos is required (require to make DualList component read only)
</script>

<template>
  <CmkIndent>
    <div>
      <h2>{{ _t('View name') }}</h2>
      <ContentSpacer :height="10" />
      <SelectorView v-model:selected-view="referencedView" :read-only="false" />
    </div>
    <ContentSpacer :height="10" />
    <div v-if="referencedView">
      <SingleInfosSpecifier
        v-model:context-infos="contextInfos"
        v-model:restricted-ids="restrictedToSingleInfos"
        v-model:mode="singleInfosMode"
      />
    </div>
  </CmkIndent>
</template>
