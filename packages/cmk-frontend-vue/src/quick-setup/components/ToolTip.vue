<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/tooltip'

const DEFAULT_DELAY: number = 200
const DEFAULT_ICON: string = 'main_help'

interface ToolTipInterface {
  /** @property {number} duration - how many milliseconds should wait before displaying the tooltip  */
  delayDuration?: number

  /** @property {number} width - Height in pixels for the tooltip icon */
  width?: number

  /** @property {number} height - Height in pixels for the tooltip icon */
  height?: number

  /** @property {string} icon - URL of the icon to display */
  icon?: string
}

const props = defineProps<ToolTipInterface>()
</script>

<template>
  <TooltipProvider :delay-duration="delayDuration || DEFAULT_DELAY">
    <Tooltip>
      <TooltipTrigger as-child>
        <CmkIcon :name="props.icon || DEFAULT_ICON" variant="inline" />
      </TooltipTrigger>
      <TooltipContent as-child class="qs-tooltip__content message">
        <div>
          <slot></slot>
        </div>
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
</template>

<style scoped>
.qs-tooltip__content {
  padding: 6px 12px;
  border-radius: 4px;
  line-height: 1;
  user-select: none;
  animation-duration: 400ms;
  animation-timing-function: cubic-bezier(0.16, 1, 0.3, 1);
  will-change: transform, opacity;
}
</style>
