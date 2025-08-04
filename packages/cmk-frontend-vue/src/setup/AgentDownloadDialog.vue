<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import CmkDialog from '@/components/CmkDialog.vue'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'
import AgentInstallSlideOutContent from '@/mode-host/agent-connection-test/components/AgentInstallSlideOutContent.vue'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/tooltip'
import { TooltipArrow } from 'radix-vue'
import usei18n from '@/lib/i18n'
import { type AgentSlideout } from 'cmk-shared-typing/typescript/agent_slideout'

const { t } = usei18n('svc_disc_agent_download')

interface Props {
  dialog_title: string
  dialog_message: string
  slide_in_title: string
  slide_in_button_title: string
  docs_button_title: string
  host_name: string
  agent_slideout: AgentSlideout
  all_agents_url: string
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
    <AgentInstallSlideOutContent
      :all_agents_url="all_agents_url"
      :host_name="host_name"
      :agent_install_cmds="agent_slideout.agent_install_cmds"
      :agent_registration_cmds="agent_slideout.agent_registration_cmds"
      :close_button_title="
        t('svc_disc_agent_download_close_title', 'Close & run service discovery')
      "
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
