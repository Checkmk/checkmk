<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclBaseCellCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['—'],
    description:
      "No interactive affordances. The cell renders a plain <td> and inherits the table's keyboard semantics."
  }
]

export const panelConfig = {
  defaultContent: {
    type: 'string' as const,
    title: 'default slot',
    initialState: 'host-01.example.com',
    help: 'Content rendered into the cell when no breakpoints are configured.'
  },
  linkEnabled: {
    type: 'boolean' as const,
    title: 'linkedTo',
    initialState: false,
    help: 'Wrap the cell content in an <a> tag.'
  },
  linkHref: {
    type: 'string' as const,
    title: '↳ href',
    initialState: 'https://checkmk.com'
  },
  linkTarget: {
    type: 'list' as const,
    title: '↳ target',
    options: [
      { title: '_self', name: '_self' },
      { title: '_blank', name: '_blank' }
    ],
    initialState: '_self'
  },
  linkVariant: {
    type: 'list' as const,
    title: '↳ variant',
    options: [
      { title: 'inline', name: 'inline' },
      { title: 'icon', name: 'icon' }
    ],
    initialState: 'inline'
  },
  highlightEnabled: {
    type: 'boolean' as const,
    title: 'highlight',
    initialState: false,
    help: 'Apply a coloured highlight to the cell.'
  },
  highlightType: {
    type: 'list' as const,
    title: '↳ type',
    options: [
      { title: 'inline', name: 'inline' },
      { title: 'outline', name: 'outline' },
      { title: 'full', name: 'full' }
    ],
    initialState: 'inline'
  },
  highlightColor: {
    type: 'list' as const,
    title: '↳ color',
    options: [
      { title: 'default', name: 'default' },
      { title: 'success', name: 'success' },
      { title: 'warning', name: 'warning' },
      { title: 'danger', name: 'danger' },
      { title: 'info', name: 'info' }
    ],
    initialState: 'default'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { computed, ref } from 'vue'

import type { CellLink } from '@/monitoring/shared/components/cell/BaseCell.vue'
import BaseCell from '@/monitoring/shared/components/cell/BaseCell.vue'
import type { CellHighlight } from '@/monitoring/shared/components/cell/base/HighlightWrapper.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const linkedTo = computed<CellLink | undefined>(() =>
  propState.value.linkEnabled
    ? {
        href: propState.value.linkHref,
        target: propState.value.linkTarget,
        variant: propState.value.linkVariant as CellLink['variant']
      }
    : undefined
)

const highlight = computed<CellHighlight | undefined>(() =>
  propState.value.highlightEnabled
    ? {
        type: propState.value.highlightType as CellHighlight['type'],
        color: propState.value.highlightColor as CellHighlight['color']
      }
    : undefined
)

const LINK_SUB_KEYS = ['linkHref', 'linkTarget', 'linkVariant'] as const
const HIGHLIGHT_SUB_KEYS = ['highlightType', 'highlightColor'] as const

const visibleConfig = computed(() =>
  Object.fromEntries(
    Object.entries(panelConfig).filter(([key]) => {
      if (!propState.value.linkEnabled && (LINK_SUB_KEYS as readonly string[]).includes(key)) {
        return false
      }
      if (
        !propState.value.highlightEnabled &&
        (HIGHLIGHT_SUB_KEYS as readonly string[]).includes(key)
      ) {
        return false
      }
      return true
    })
  )
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>BaseCell</UclDetailPageHeader>

    <UclDetailPageComponent>
      <table class="ucl-base-cell__table">
        <tbody>
          <tr>
            <BaseCell :linked-to="linkedTo" :highlight="highlight">
              {{ propState.defaultContent }}
            </BaseCell>
          </tr>
        </tbody>
      </table>

      <template #properties>
        <UclPropertiesPanel
          v-model="propState"
          :config="visibleConfig"
          class="ucl-base-cell__panel"
        />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-base-cell__table {
  border-collapse: collapse;
  width: 250px;
}

/* stylelint-disable selector-pseudo-class-no-unknown */
.ucl-base-cell__table :deep(td) {
  border: 1px solid var(--ux-theme-6);
}

.ucl-base-cell__panel :deep(div:has(> div > label[for$='-linkHref'])),
.ucl-base-cell__panel :deep(div:has(> div > label[for$='-linkTarget'])),
.ucl-base-cell__panel :deep(div:has(> div > label[for$='-linkVariant'])),
.ucl-base-cell__panel :deep(div:has(> div > label[for$='-highlightType'])),
.ucl-base-cell__panel :deep(div:has(> div > label[for$='-highlightColor'])),
.ucl-base-cell__panel :deep(div:has(> div > label[for$='-highlightOutline'])) {
  padding-left: 16px;
}
/* stylelint-enable selector-pseudo-class-no-unknown */
</style>
