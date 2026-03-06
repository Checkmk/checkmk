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
import type { ConfiguredFilters } from '@/dashboard/components/filter/types.ts'
import SelectorView from '@/dashboard/components/selectors/SelectorView.vue'
import { useInjectViews } from '@/dashboard/composables/useProvideViews'
import type { DataSourceModel } from '@/dashboard/types/api'
import { RestrictedToSingle } from '@/dashboard/types/shared.ts'

const { _t } = usei18n()

const props = defineProps<{
  datasourcesById: Record<string, DataSourceModel>
}>()

const emit = defineEmits<{
  (e: 'overwrite-filters', filters: ConfiguredFilters): void
}>()

const referencedView = defineModel<string | null>('referencedView', { default: null })
const contextInfos = defineModel<string[]>('contextInfos', { default: [] })
const restrictedToSingleInfos = defineModel<string[]>('restrictedToSingleInfos', {
  default: []
})
const singleInfosMode = ref<RestrictedToSingle>(RestrictedToSingle.NO)

const byViewId = useInjectViews()

watch(
  () => referencedView.value,
  (id) => {
    if (!id) {
      contextInfos.value = []
      emit('overwrite-filters', {})
      return
    }

    const view = byViewId.value[id]
    // Use prop for synchronous access to avoid timing issues
    const datasource = props.datasourcesById[view!.extensions!.data_source]

    const newInfos = datasource!.extensions.infos
    // Equality check to prevent unnecessary resets
    const currentInfos = contextInfos.value
    const hasChanged =
      newInfos.length !== currentInfos.length || newInfos.some((v, i) => v !== currentInfos[i])

    if (hasChanged) {
      contextInfos.value = newInfos
    }

    const restrictedToSingle = view!.extensions?.restricted_to_single ?? []

    if (restrictedToSingle.length === 1 && restrictedToSingle[0] === 'host') {
      singleInfosMode.value = RestrictedToSingle.HOST
    } else if (restrictedToSingle.length > 0) {
      singleInfosMode.value = RestrictedToSingle.CUSTOM
    } else {
      singleInfosMode.value = RestrictedToSingle.NO
    }
    restrictedToSingleInfos.value = restrictedToSingle
    emit('overwrite-filters', (view!.extensions?.filters ?? {}) as unknown as ConfiguredFilters)
  },
  { immediate: true }
)
</script>

<template>
  <CmkIndent>
    <div>
      <h2>{{ _t('View name') }}</h2>
      <ContentSpacer :dimension="5" />
      <SelectorView v-model:selected-view="referencedView" :read-only="false" />
    </div>
    <template v-if="referencedView">
      <ContentSpacer :dimension="5" />
      <div>
        <SingleInfosSpecifier
          v-model:context-infos="contextInfos"
          v-model:restricted-ids="restrictedToSingleInfos"
          v-model:mode="singleInfosMode"
          :read-only="true"
        />
      </div>
    </template>
  </CmkIndent>
</template>
