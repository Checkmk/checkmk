<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkAccordion from '@/components/CmkAccordion/CmkAccordion.vue'
import CmkAccordionItem from '@/components/CmkAccordion/CmkAccordionItem.vue'
import CmkAccordionItemStateIndicator from '@/components/CmkAccordion/CmkAccordionItemStateIndicator.vue'
import CmkCode from '@/components/CmkCode.vue'
import { CmkWizardButton } from '@/components/CmkWizard'
import CmkWizardStep from '@/components/CmkWizard/CmkWizardStep.vue'
import { getWizardContext } from '@/components/CmkWizard/utils.ts'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import type { AgentSlideOutTabs } from '../../lib/type_def'
import GenerateToken from '../GenerateToken.vue'

const { _t } = usei18n()

const props = defineProps<{
  index: number
  isCompleted: () => boolean
  tab: AgentSlideOutTabs
  isPushMode: boolean
  closeButtonTitle: TranslatedString
  hostName: string
  userSettingsUrl: string
}>()

const emit = defineEmits(['close'])
const context = getWizardContext()
const ott = ref<string | null | Error>(null)
const accordionOpen = ref<string[]>([])

const regAgentOttCmd = computed(() => {
  if (props.tab.registrationCmd) {
    if (ott.value && !(ott.value instanceof Error)) {
      return props.tab.registrationCmd?.replace('--user agent_registration', `--ott 0:${ott.value}`)
    }

    return props.tab.registrationCmd
  } else {
    return ''
  }
})

function reset() {
  ott.value = null
}
</script>
<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading> {{ _t('Register agent') }}</CmkHeading>
    </template>
    <template #content>
      <div v-if="context.isSelected(index)">
        <div v-if="tab.registrationMsg && tab.registrationCmd">
          <div class="register-heading-row">
            <CmkParagraph>
              {{
                _t(
                  `Agent registration will establish trust between the Agent Controller
                    on the host and the Agent Receiver on the Checkmk server.`
                )
              }}
            </CmkParagraph>
          </div>

          <GenerateToken
            v-model="ott"
            token-generation-endpoint-uri="domain-types/agent_registration_token/collections/all"
            :expires-in-days="7"
            :token-generation-body="{
              host: hostName,
              comment: 'Agent registration token for agent slideout'
            }"
            :description="_t('This requires the generation of a registration token.')"
          />
          <template v-if="ott !== null">
            <CmkParagraph>{{ tab.registrationMsg }}</CmkParagraph>
            <CmkCode :code_txt="regAgentOttCmd" class="code" />
          </template>
        </div>
      </div>
      <div v-else>
        <CmkParagraph>
          {{ _t('Run this command to register the Checkmk agent controller.') }}
        </CmkParagraph>
      </div>
      <CmkAccordion v-model="accordionOpen" :min-open="0" class="mh-register-agent__panel">
        <CmkAccordionItem value="authenticate-with-user">
          <template #header>
            <CmkAccordionItemStateIndicator value="authenticate-with-user" />
            {{ _t('Troubleshooting registration issues: Authenticate with the registration user') }}
          </template>
          <template #content>
            <CmkParagraph>
              {{
                _t(`Registration fails if the token cannot be authorized. In this case,
              authenticate using the`)
              }}
              <b>{{ _t('agent_registration') }}</b>
              {{ _t(`user instead of the token.`) }}
            </CmkParagraph>
            <br />
            <CmkParagraph>
              {{
                _t(
                  `When you run the command in the terminal, you will be prompted for the password of the`
                )
              }}
              <a :href="userSettingsUrl" target="_blank"> {{ _t('agent_registration user') }}</a> .
              {{
                _t(`Copy the 'Automation secret for machine accounts' from the agent_registration
                   user and paste it into the terminal to continue the registration.`)
              }}
            </CmkParagraph>
            <CmkCode :code_txt="regAgentOttCmd" class="code" />
          </template>
        </CmkAccordionItem>
      </CmkAccordion>
    </template>
    <template v-if="context.isSelected(index)" #actions>
      <CmkWizardButton
        v-if="!isPushMode"
        type="finish"
        :override-label="closeButtonTitle"
        :disabled="ott === null"
        icon-name="connection-tests"
        @click="emit('close')"
      />
      <CmkWizardButton v-else type="next" :disabled="ott === null" />
      <CmkWizardButton type="previous" @click="reset" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
.mh-register-agent__panel {
  max-width: 650px;
}
</style>
