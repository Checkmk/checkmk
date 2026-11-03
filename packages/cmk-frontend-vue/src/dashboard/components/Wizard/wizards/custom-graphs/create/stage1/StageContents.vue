<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useTemplateRef } from 'vue'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'

import ActionBar from '../../../../components/ActionBar.vue'
import ActionButton from '../../../../components/ActionButton.vue'
import CustomGraphEditor from '../../editor/CustomGraphEditor.vue'
import type { UseEmbeddedCustomGraph } from '../composables/useEmbeddedCustomGraph'

const { _t } = usei18n()

const handler = defineModel<UseEmbeddedCustomGraph>('handler', { required: true })

const emit = defineEmits<{
  goNext: []
}>()

const editor = useTemplateRef('editor')

function gotoNextStage(): void {
  const definition = editor.value?.submit() ?? null
  if (definition !== null) {
    handler.value.dataSources.value = definition.data_sources
    emit('goNext')
  }
}
</script>

<template>
  <div class="db-stage-contents">
    <div>
      <CmkHeading type="h1">
        {{ _t('Data selection') }}
      </CmkHeading>

      <ContentSpacer />

      <ActionBar align-items="left">
        <ActionButton
          :label="_t('Next step: Widget settings')"
          :icon="{ name: 'continue', side: 'right' }"
          :action="gotoNextStage"
          variant="secondary"
        />
      </ActionBar>

      <ContentSpacer />
    </div>

    <Suspense>
      <CustomGraphEditor
        ref="editor"
        v-model:graph-options="handler.graphOptions.value"
        :title="handler.visualization.title.value"
        :time-range="handler.previewTimeRange.value"
        :data-sources="handler.dataSources.value"
      />
      <template #fallback>
        <CmkIcon name="load-graph" size="xxlarge" />
      </template>
    </Suspense>
  </div>
</template>

<style scoped>
/* Bounds the designer to the stage's height, so only its tabs scroll and the preview stays put. */
.db-stage-contents {
  display: flex;
  flex-direction: column;
  height: 100%;
}
</style>
