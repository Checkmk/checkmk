<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

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
}>()

const emit = defineEmits(['close'])
const context = getWizardContext()
const ott = ref<string | null | Error>(null)
const ottExpiryDate = new Date()
ottExpiryDate.setDate(ottExpiryDate.getDate() + 7)

const regAgentCmd = computed(() => {
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
            :token-generation-body="{
              host: hostName,
              comment: 'Agent registration token for agent slideout',
              expires_at: ottExpiryDate
            }"
            :description="_t('This requires the generation of a registration token.')"
          />
          <template v-if="ott !== null">
            <CmkParagraph>{{ tab.registrationMsg }}</CmkParagraph>
            <CmkCode :code_txt="regAgentCmd" class="code" />
          </template>
        </div>
      </div>
      <div v-else>
        <CmkParagraph>
          {{ _t('Run this command to register the Checkmk agent controller.') }}
        </CmkParagraph>
      </div>
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
