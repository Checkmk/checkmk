<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'

import { useInjectMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction.ts'
import { type EffectiveWidgetFilterContext } from '@/dashboard/types/widget.ts'

interface Props {
  renderContext?: 'configurationPreview' | 'activeDashboard'
  effectiveFilterContext: EffectiveWidgetFilterContext
}
const { renderContext = 'activeDashboard', effectiveFilterContext } = defineProps<Props>()
const { _t } = usei18n()

const enterMissingRuntimeFiltersAction = useInjectMissingRuntimeFiltersAction()

const missingSingleInfosString = computed(() => {
  const missingSingleInfos = effectiveFilterContext.restricted_to_single.filter(
    (key: string) => !(key in effectiveFilterContext.filters)
  )
  return missingSingleInfos.sort().join(', ')
})
</script>

<template>
  <div v-if="enterMissingRuntimeFiltersAction !== null" class="db-missing-filters-msg">
    <div>
      <a @click="enterMissingRuntimeFiltersAction()">{{ _t('Enter runtime filter') }}</a>
      <span v-if="renderContext === 'configurationPreview'">{{ _t('to load preview') }}</span>
      <span v-else>{{ _t('to load data') }}</span>
    </div>
  </div>
  <CmkAlertBox v-else-if="missingSingleInfosString!!" variant="warning">
    {{
      _t(
        'This widget cannot be displayed because required context information is missing (%{ missingSingleInfosString }). Please add dashboard or widget filters to provide the missing context.',
        { missingSingleInfosString }
      )
    }}
  </CmkAlertBox>
  <slot v-else />
</template>

<style scoped>
.db-missing-filters-msg {
  display: flex;
  height: 100%;
  background-color: var(--db-content-bg-color);

  > div {
    width: 100%;
    text-align: center;
    margin: auto 0;
    line-height: var(--dimension-7);

    > a {
      cursor: pointer;
      text-decoration: underline;
    }

    > span {
      display: block;
      color: var(--font-color-breadcrumb-inactive);
    }
  }
}
</style>
