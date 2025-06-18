<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import CmkDialog from '@/components/CmkDialog.vue'
import SlideIn from '@/components/SlideIn.vue'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/tooltip'
import { TooltipArrow } from 'radix-vue'

interface Props {
  dialog_title: string
  dialog_message: string
  slide_in_title: string
  slide_in_button_title: string
  docs_button_title: string
  url: string
}

defineProps<Props>()

const slideInOpen = ref(false)
const externalContent = ref('')

const openDocs = () => {
  window.open('https://docs.checkmk.com/latest/en/wato_monitoringagents.html#agents', '_blank')
}

const tooltipOpen = ref(true)
</script>

<template>
  <TooltipProvider>
    <Tooltip :open="tooltipOpen" class="tooltip">
      <TooltipTrigger as="span"></TooltipTrigger>
      <TooltipContent align="center" side="right" :avoid-collisions="false" class="tooltip-content">
        <TooltipArrow
          :style="{ fill: 'var(--default-help-icon-bg-color)' }"
          :width="6"
          :height="6"
        />
        <!-- eslint-disable-next-line vue/no-bare-strings-in-template -->
        <button class="tooltip-close" @click.prevent="tooltipOpen = false">×</button>
        <CmkDialog
          :title="dialog_title"
          :message="dialog_message"
          :buttons="[
            {
              title: slide_in_button_title,
              onclick: () => {
                slideInOpen = true
              },
              variant: 'info'
            },
            {
              title: docs_button_title,
              onclick: () => {
                openDocs()
              },
              variant: 'optional'
            }
          ]"
          class="agent-download-dialog__dialog"
        />
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
  <SlideIn
    :open="slideInOpen"
    :header="{ title: slide_in_title, closeButton: true }"
    @close="slideInOpen = false"
  >
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div v-html="externalContent"></div>
  </SlideIn>
</template>

<style scoped>
.agent-download-dialog__dialog {
  margin: 0 !important;
}

.tooltip-close {
  position: absolute;
  top: 2px;
  right: 4px;
  background: transparent;
  border: none;
  cursor: pointer;
  margin: 0;
  padding: 0;
}
</style>
