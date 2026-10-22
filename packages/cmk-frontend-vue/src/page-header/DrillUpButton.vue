<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!-- Leads back to the page a drill-down came from. -->
<script setup lang="ts">
import { type DrillUpButton } from 'cmk-shared-typing/typescript/drill_up_button'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

import { drillUpTarget } from './drillUp'

const { _t } = usei18n()

const props = defineProps<DrillUpButton>()

const target = drillUpTarget(window.history.length, document.referrer, window.location.href)
const label = _t('Back to %{title}', { title: props.title })
const tooltipOpen = ref(false)

function drillUp(): void {
  if (target === 'history') {
    window.history.back()
  } else if (target !== null) {
    window.location.assign(target)
  }
}
</script>

<template>
  <CmkTooltipProvider v-if="target !== null" :delay-duration="200">
    <CmkTooltip v-model:open="tooltipOpen">
      <CmkTooltipTrigger as-child>
        <button
          type="button"
          class="page-header-drill-up-button"
          :aria-label="label"
          @click="drillUp"
        >
          <CmkMultitoneIcon name="back" primary-color="font" size="large" />
        </button>
      </CmkTooltipTrigger>
      <CmkTooltipContent side="bottom" align="start">{{ label }}</CmkTooltipContent>
    </CmkTooltip>
  </CmkTooltipProvider>
</template>

<style scoped>
.page-header-drill-up-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--dimension-2);
  border: none;
  border-radius: 2px;
  background: none;
  cursor: pointer;

  &:hover {
    background-color: color-mix(in srgb, var(--font-color) 10%, transparent);
  }
}
</style>
