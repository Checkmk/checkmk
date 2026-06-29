<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import type { ActionFormDefinition } from '@/monitoring/shared/components/action/types'

import codeExample from './UclActionFormPaneCodeExample.vue?raw'

type ActionType = ActionFormDefinition['type']

const TYPE_OPTIONS: Options<ActionType>[] = [
  { title: 'Confirm (no inputs)', name: 'confirm' },
  { title: 'Comment', name: 'comment' }
]

export const panelConfig = {
  type: {
    type: 'list' as const,
    title: 'definition.type',
    options: TYPE_OPTIONS,
    initialState: 'comment' as ActionType,
    help: 'The action form type. The pane renders the matching form from its registry; "confirm" has no inputs.'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { computed, ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import ActionFormPane from '@/monitoring/shared/components/action/ActionFormPane.vue'
import type { ActionFormValues } from '@/monitoring/shared/components/action/types'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const TITLES: Record<ActionType, TranslatedString> = {
  confirm: 'Reschedule check' as TranslatedString,
  comment: 'Add comment' as TranslatedString
}

const subtitle = 'web-server-01' as TranslatedString

const definition = computed<ActionFormDefinition>(() => ({
  type: propState.value.type,
  ident: propState.value.type
}))

const lastSubmitted = ref<string | null>(null)

function onSubmit(values: ActionFormValues): void {
  lastSubmitted.value = JSON.stringify(values)
}

function onCancel(): void {
  lastSubmitted.value = 'cancelled'
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>ActionFormPane</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-action-form-pane__stack">
        <div class="ucl-action-form-pane__container">
          <ActionFormPane
            :definition="definition"
            :title="TITLES[propState.type]"
            :subtitle="subtitle"
            @submit="onSubmit"
            @cancel="onCancel"
          />
        </div>

        <p class="ucl-action-form-pane__hint">
          The pane renders the form for <code>definition.type</code> from its registry, mirroring
          how the filter dropdown switches on a filter's type. Last result:
          <strong>{{ lastSubmitted ?? '—' }}</strong>
        </p>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-action-form-pane__stack {
  display: flex;
  flex-direction: column;
  align-items: start;
  gap: var(--dimension-4);
  width: 100%;
}

.ucl-action-form-pane__container {
  width: 360px;
  max-width: 100%;
  height: 360px;
  border: 1px dashed var(--ux-theme-6);
  border-radius: 4px;
  box-sizing: border-box;
}

.ucl-action-form-pane__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
