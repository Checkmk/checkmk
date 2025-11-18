<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from '@/components/CmkTooltip'

const showTopTooltip = ref(false)
defineProps<{ screenshotMode: boolean }>()

const toggleTooltip = () => {
  showTopTooltip.value = !showTopTooltip.value
}

const hideTooltip = () => {
  showTopTooltip.value = false
}
</script>

<template>
  <div>
    <div>
      <CmkTooltipProvider>
        <CmkTooltip :open="showTopTooltip">
          <CmkTooltipTrigger as-child>
            <CmkButton variant="secondary" @click="toggleTooltip">
              <CmkIcon name="checkmark" variant="inline" size="small" />
            </CmkButton>
          </CmkTooltipTrigger>
          <CmkTooltipContent side="top" align="center" @pointer-down-outside="hideTooltip">
            <div class="tooltip-content">
              <CmkIcon name="checkmark" variant="inline" size="small" />
              Tooltip on top
            </div>
          </CmkTooltipContent>
        </CmkTooltip>
      </CmkTooltipProvider>
    </div>
  </div>
</template>
