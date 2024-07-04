<script setup lang="ts">
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

const DEFAULT_DELAY: number = 200
const DEFAULT_HEIGHT: number = 16
const DEFAULT_ICON: string = 'themes/facelift/images/icon_about_checkmk.svg'

interface ToolTipInterface {
  /** @property {number} duration - how many milliseconds should wait before displaying the tooltip  */
  delayDuration?: number

  /** @property {number} height - Height in pixels for the tooltip icon */
  height?: number

  /** @property {string} icon - URL of the icon to display */
  icon?: string
}

defineProps<ToolTipInterface>()
</script>

<template>
  <TooltipProvider :delay-duration="delayDuration || DEFAULT_DELAY">
    <Tooltip>
      <TooltipTrigger as-child>
        <img class="trigger" :src="icon || DEFAULT_ICON" :height="height || DEFAULT_HEIGHT" />
      </TooltipTrigger>
      <TooltipContent as-child class="tooltipContent message">
        <div>
          <slot></slot>
        </div>
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
</template>

<style scoped>
.trigger {
  cursor: pointer;
  position: relative;
  top: 4px;
}

div.message {
  padding: 4px;
  margin: 0;
}

.tooltipContent {
  border-radius: 4px;
  line-height: 1;
  box-shadow:
    hsl(206 22% 7% / 35%) 0px 10px 38px -10px,
    hsl(206 22% 7% / 20%) 0px 10px 20px -15px;
  user-select: none;
  animation-duration: 400ms;
  animation-timing-function: cubic-bezier(0.16, 1, 0.3, 1);
  will-change: transform, opacity;
}
</style>
