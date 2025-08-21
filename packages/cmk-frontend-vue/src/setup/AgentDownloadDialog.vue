<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import CmkDialog from '@/components/CmkDialog.vue'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/tooltip'
import { TooltipArrow } from 'radix-vue'
import { type AgentSlideout } from 'cmk-shared-typing/typescript/agent_slideout'
import AgentSlideOutContent from '@/mode-host/agent-connection-test/components/AgentSlideOutContent.vue'

interface Props {
  dialog_title: string
  dialog_message: string
  slide_in_title: string
  slide_in_button_title: string
  docs_button_title: string
  close_button_title: string
  agent_slideout: AgentSlideout
  all_agents_url: string
  is_not_registered: boolean
}

defineProps<Props>()

const slideInOpen = ref(false)

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
  <CmkSlideInDialog
    :open="slideInOpen"
    :header="{ title: slide_in_title, closeButton: true }"
    @close="slideInOpen = false"
  >
    <AgentSlideOutContent
      :all-agents-url="all_agents_url"
      :host-name="agent_slideout.host_name"
      :agent-install-cmds="agent_slideout.agent_install_cmds"
      :agent-registration-cmds="agent_slideout.agent_registration_cmds"
      :legacy-agent-url="agent_slideout.legacy_agent_url"
      :close-button-title="close_button_title"
      :save-host="agent_slideout.save_host"
      :agent-installed="is_not_registered"
      :is-push-mode="false"
      @close="((slideInOpen = false), (tooltipOpen = false))"
    />
  </CmkSlideInDialog>
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
