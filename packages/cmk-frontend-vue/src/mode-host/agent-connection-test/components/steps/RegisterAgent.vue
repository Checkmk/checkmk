<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkCode from 'cmk-ui-library/components/CmkCode.vue'
import CmkCollapsible from 'cmk-ui-library/components/CmkCollapsible'
import CmkCollapsibleTitle from 'cmk-ui-library/components/CmkCollapsible/CmkCollapsibleTitle.vue'
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import { CmkWizardButton } from 'cmk-ui-library/components/CmkWizard'
import CmkWizardStep from 'cmk-ui-library/components/CmkWizard/CmkWizardStep.vue'
import { getWizardContext } from 'cmk-ui-library/components/CmkWizard/utils.ts'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref, watch } from 'vue'

import { applyToken, isResolved, requiresToken } from '../../lib/commandTemplate'
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
  siteId: string
  userSettingsUrl: string
  agentReceiverPortIsDefault: boolean
}>()

const selectedVariantId = defineModel<string>('selectedVariantId', { default: '' })
const emit = defineEmits(['close'])
const context = getWizardContext()
const ott = ref<string | null | Error>(null)
const collapsibleOpen = ref<boolean>(false)

const activeRegistrationCmd = computed<string | undefined>(() => {
  const variants = props.tab.registrationCmdVariants
  if (variants && variants.length > 0) {
    return variants.find((v) => v.id === selectedVariantId.value)?.cmd ?? variants[0]!.cmd
  }
  return props.tab.registrationCmd
})

const registrationCmd = computed(() =>
  applyToken(activeRegistrationCmd.value, 'registration', ott.value)
)

/** Whether the token command can be shown as it stands. */
const commandShown = computed(() => isResolved(registrationCmd.value.tokenState))

/** Whether this command needs a token at all. */
const needsToken = computed(() => requiresToken(activeRegistrationCmd.value, 'registration'))

/**
 * Latches once a generation attempt failed. Retrying puts the token back to
 * `missing`, so without the latch the button would lock again while the
 * fallback command is still on screen.
 */
const generationFailed = ref(false)

/**
 * Registering with the agent_registration user is a legitimate way to finish
 * this step, so a failed attempt must not lock the user in - only a token that
 * nobody has tried to generate yet does.
 */
const waitingForToken = computed(
  () => !generationFailed.value && registrationCmd.value.tokenState === 'missing'
)

// A warning that points at the troubleshooting section is useless while that
// section is folded away.
watch(
  () => registrationCmd.value.tokenState,
  (state) => {
    if (state === 'failed') {
      generationFailed.value = true
      collapsibleOpen.value = true
    }
  }
)

/** Leaving the step backwards discards the attempt along with the token. */
function reset() {
  ott.value = null
  generationFailed.value = false
}
</script>
<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading> {{ _t('Register agent') }}</CmkHeading>
    </template>
    <template #content>
      <div v-if="context.isSelected(index)">
        <div v-if="tab.registrationMsg && (tab.registrationCmd || tab.registrationCmdVariants)">
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
            v-if="needsToken"
            v-model="ott"
            token-generation-endpoint-uri="domain-types/agent_registration_token/collections/all"
            :expires-in-seconds="604800"
            :token-generation-body="{
              host: hostName,
              comment: 'Agent registration token for agent slideout',
              site_id: siteId
            }"
            :description="_t('This requires the generation of a registration token.')"
          />
          <CmkAlertBox
            v-if="registrationCmd.tokenState === 'failed'"
            variant="warning"
            size="small"
          >
            {{
              _t(
                'The registration command is hidden until a token has been generated successfully. You can register with the agent_registration user instead - see "Troubleshooting registration issues" below.'
              )
            }}
          </CmkAlertBox>
          <template v-if="commandShown">
            <CmkToggleButtonGroup
              v-if="tab.registrationCmdVariants && tab.registrationCmdVariants.length > 1"
              v-model="selectedVariantId"
              class="mh-register-agent__shell-toggle"
              :options="tab.registrationCmdVariants.map((v) => ({ label: v.label, value: v.id }))"
            />
            <CmkParagraph>{{ tab.registrationMsg }}</CmkParagraph>
            <CmkCode :code-text="registrationCmd.text" class="code" width="fill" />
            <CmkAlertBox v-if="agentReceiverPortIsDefault" variant="warning" size="small">
              {{
                _t(
                  'The agent receiver port could not be determined from the remote site. The command uses the default port (8000). Adjust the --server port if your site uses a different agent receiver port.'
                )
              }}
            </CmkAlertBox>
          </template>
        </div>
      </div>
      <div v-else>
        <CmkParagraph>
          {{ _t('Run this command to register the Checkmk agent controller.') }}
        </CmkParagraph>
      </div>

      <CmkCollapsibleTitle
        :open="collapsibleOpen"
        :title="_t('Troubleshooting registration issues: Authenticate with the registration user')"
        @toggle-open="collapsibleOpen = !collapsibleOpen"
      />
      <CmkCollapsible :open="collapsibleOpen">
        <CmkIndent>
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
                `When you run the command in the terminal, you will be prompted for the password of the
                agent_registration user. Copy the 'Automation secret for machine accounts' from the `
              )
            }}
            <a :href="userSettingsUrl" target="_blank"> {{ _t('agent_registration user') }}</a>
            {{ _t(`and paste it into the terminal to continue the registration.`) }}
          </CmkParagraph>
          <CmkToggleButtonGroup
            v-if="tab.registrationCmdVariants && tab.registrationCmdVariants.length > 1"
            v-model="selectedVariantId"
            class="mh-register-agent__shell-toggle"
            :options="tab.registrationCmdVariants.map((v) => ({ label: v.label, value: v.id }))"
          />
          <CmkCode :code-text="activeRegistrationCmd ?? ''" class="code" width="fill" />
        </CmkIndent>
      </CmkCollapsible>
    </template>
    <template v-if="context.isSelected(index)" #actions>
      <CmkWizardButton
        v-if="!isPushMode"
        type="finish"
        :override-label="closeButtonTitle"
        :disabled="waitingForToken"
        icon-name="connection-tests"
        @click="emit('close')"
      />
      <CmkWizardButton v-else type="next" :disabled="waitingForToken" />
      <CmkWizardButton type="previous" @click="reset" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */

/* `.code` and `.register-heading-row` used to be declared in AgentSlideOut's
   scoped style, where they never matched this component's elements. */
.code {
  margin: var(--dimension-5) 0 var(--dimension-7);
  width: 100%;
}

.register-heading-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-4);
}

.mh-register-agent__panel {
  max-width: 650px;
}

.mh-register-agent__shell-toggle {
  margin-top: var(--dimension-5);
  margin-bottom: var(--dimension-5);
}
</style>
