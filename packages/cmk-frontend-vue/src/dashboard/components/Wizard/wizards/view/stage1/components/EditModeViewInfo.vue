<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'

import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import SingleInfosSpecifier from '@/dashboard/components/Wizard/wizards/view/stage1/components/SingleInfosSpecifier.vue'
import { useInjectViews } from '@/dashboard/composables/useProvideViews'
import type { DataSourceModel } from '@/dashboard/types/api'
import { RestrictedToSingle } from '@/dashboard/types/shared.ts'
import type { EmbeddedViewContent, LinkedViewContent } from '@/dashboard/types/widget'

const { _t } = usei18n()

interface Props {
  content: EmbeddedViewContent | LinkedViewContent
  contextInfos: string[]
  restrictedToSingleInfos: string[]
  datasourcesById: Record<string, DataSourceModel>
}
const props = defineProps<Props>()

const byViewId = useInjectViews()

const viewTitle = computed(() => {
  if (props.content.type === 'linked_view') {
    return byViewId.value[props.content.view_name]?.title ?? props.content.view_name
  }
  return ''
})

const datasourceTitle = computed(() => {
  if (props.content.type === 'embedded_view') {
    return props.datasourcesById[props.content.datasource]?.title ?? props.content.datasource
  }
  return ''
})

const singleInfosMode = computed<RestrictedToSingle>(() => {
  if (props.restrictedToSingleInfos.length === 1 && props.restrictedToSingleInfos[0] === 'host') {
    return RestrictedToSingle.HOST
  } else if (props.restrictedToSingleInfos.length > 0) {
    return RestrictedToSingle.CUSTOM
  } else {
    return RestrictedToSingle.NO
  }
})
</script>

<template>
  <div class="db-edit-mode-view-info__container">
    <div v-if="content.type === 'linked_view'">
      <CmkIndent>
        <div class="info-value-block">
          <span class="db-edit-mode-view-info__info-label">{{ _t('Linked to view') }}</span>
          <div class="db-edit-mode-view-info__info-value">{{ viewTitle }}</div>
          <ContentSpacer :dimension="5" />
          <SingleInfosSpecifier
            :context-infos="contextInfos"
            :restricted-ids="restrictedToSingleInfos"
            :mode="singleInfosMode"
            :read-only="true"
          />
        </div>
      </CmkIndent>
    </div>
    <div v-if="content.type === 'embedded_view'">
      <CmkIndent>
        <div class="info-value-block">
          <span class="db-edit-mode-view-info__info-label">{{ _t('Datasource') }}</span>
          <div class="db-edit-mode-view-info__info-value">{{ datasourceTitle }}</div>
          <ContentSpacer :dimension="5" />
          <SingleInfosSpecifier
            :context-infos="contextInfos"
            :restricted-ids="restrictedToSingleInfos"
            :mode="singleInfosMode"
            :read-only="true"
          />
        </div>
      </CmkIndent>
    </div>
  </div>
</template>

<style scoped>
.db-edit-mode-view-info__container {
  padding: var(--dimension-5) 0;
}

.db-edit-mode-view-info__info-label {
  font-weight: bold;
  display: block;
  margin-bottom: var(--dimension-3);
}

.db-edit-mode-view-info__info-value {
  font-weight: var(--font-weight-bold);
}
</style>
