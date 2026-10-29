<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkTruncateTextCodeExample.vue?raw'

export const panelConfig = {
  text: {
    type: 'string' as const,
    title: 'Text',
    initialState: 'This is a long text that exceeds the width of its container'
  },
  suffixCount: {
    type: 'number' as const,
    title: 'Suffix count',
    help: 'Number of trailing characters that always stay visible.',
    initialState: 6
  }
} satisfies PanelConfigFor<typeof CmkTruncateText>
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import CmkTruncateText from 'cmk-ui-library/components/CmkTruncateText.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkTruncateText>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkTruncateText</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-cmk-truncate-text">
        <p>
          Truncates in the middle: the start gets an ellipsis while the last characters stay
          visible, so paths and names stay distinguishable. Hover for the full text. Drag the box's
          bottom-right corner to change its width:
        </p>
        <div class="ucl-cmk-truncate-text__box">
          <CmkTruncateText
            :text="untranslated(propState.text)"
            :suffix-count="propState.suffixCount"
          />
        </div>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-cmk-truncate-text {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);

  > p {
    margin: 0;
  }
}

/* The text only truncates when its container is narrower than the text. */
.ucl-cmk-truncate-text__box {
  width: 200px;
  max-width: 100%;
  padding: var(--dimension-3);
  border: 1px dashed var(--ux-theme-8);
  resize: horizontal;
  overflow: hidden;
}
</style>
