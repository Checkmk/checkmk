<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkMenu from 'cmk-ui-library/components/CmkMenu'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, ref, useTemplateRef } from 'vue'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'

import ActionBar from '../../../../components/ActionBar.vue'
import ActionButton from '../../../../components/ActionButton.vue'
import type { UseEmbeddedCustomGraph } from '../../create/composables/useEmbeddedCustomGraph'
import CustomGraphEditor from '../../editor/CustomGraphEditor.vue'
import DiscardCopyPopup from '../DiscardCopyPopup.vue'
import type { UseCustomGraphClone } from '../composables/useCustomGraphClone'

const { _t } = usei18n()

const handler = defineModel<UseEmbeddedCustomGraph>('handler', { required: true })

const { cloneState } = defineProps<{ cloneState: UseCustomGraphClone }>()

const emit = defineEmits<{
  goNext: []
}>()

const editor = useTemplateRef('editor')

const pendingGraph = ref<string | null>(null)
const askDiscard = ref(false)

function pickGraph(key: string): void {
  if (key === cloneState.selected.value?.key) {
    return
  }
  if (cloneState.hasEdits(editor.value?.isModified() ?? false)) {
    pendingGraph.value = key
    askDiscard.value = true
    return
  }
  void cloneState.clone(key)
}

function discardEdits(): void {
  askDiscard.value = false
  if (pendingGraph.value !== null) {
    void cloneState.clone(pendingGraph.value)
  }
}

function gotoNextStage(): void {
  if (!cloneState.validate()) {
    return
  }
  const definition = editor.value?.submit() ?? null
  if (definition !== null) {
    if (editor.value?.isModified()) {
      cloneState.markAsEdited()
    }
    handler.value.dataSources.value = definition.data_sources
    emit('goNext')
  }
}
// Icon-only once a graph is cloned, as the heading next to it names it.
const dropdownTriggerText = computed(() =>
  cloneState.selected.value === null ? _t('Clone custom graph') : undefined
)
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

      <div class="db-stage-contents__clone-picker">
        <CmkMenu
          :items="cloneState.catalogItems.value"
          :label="_t('Clone custom graph')"
          trigger-icon="clone"
          :trigger-text="dropdownTriggerText"
          :search-placeholder="_t('Search custom graphs ...')"
          searchable
          @select="pickGraph"
        />
        <CmkHeading v-if="cloneState.selected.value !== null" type="h3">
          {{ cloneState.selected.value.title }}
        </CmkHeading>
      </div>
      <CmkInlineValidation
        v-if="cloneState.selectionErrors.value.length > 0"
        :validation="cloneState.selectionErrors.value"
      />

      <ContentSpacer />

      <CmkAlert
        v-if="cloneState.error.value !== null"
        variant="error"
        :text="untranslated(cloneState.error.value)"
      />
    </div>

    <CmkIcon v-if="cloneState.loading.value" name="load-graph" size="xxlarge" />
    <Suspense v-else-if="cloneState.selected.value !== null && cloneState.error.value === null">
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

    <DiscardCopyPopup :open="askDiscard" @confirm="discardEdits" @close="askDiscard = false" />
  </div>
</template>

<style scoped>
/* Bounds the designer to the stage's height, so only its tabs scroll and the preview stays put. */
.db-stage-contents {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.db-stage-contents__clone-picker {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}
</style>
