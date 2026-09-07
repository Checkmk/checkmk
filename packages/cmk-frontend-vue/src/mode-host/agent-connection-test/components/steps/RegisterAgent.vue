<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkCollapsible from 'cmk-ui-library/components/CmkCollapsible'
import CmkCollapsibleTitle from 'cmk-ui-library/components/CmkCollapsible/CmkCollapsibleTitle.vue'
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import { CmkWizardButton } from 'cmk-ui-library/components/CmkWizard'
import CmkWizardStep from 'cmk-ui-library/components/CmkWizard/CmkWizardStep.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref, watch } from 'vue'

import {
  type HostMacros,
  type TokenValue,
  isResolved,
  renderBlocks,
  requiresToken
} from '../../lib/commandTemplate'
import type { CommandBlock, CommandChoice, RegisterSpec } from '../../lib/types'
import CommandBlockList from '../CommandBlockList.vue'
import GenerateToken from '../GenerateToken.vue'
import ShellToggle from '../ShellToggle.vue'

const props = defineProps<{
  index: number
  isCompleted: () => boolean
  isActive: boolean
  spec: RegisterSpec
  macros: HostMacros
  /** True when no step follows, so this step finishes the wizard. */
  isLastStep: boolean
  closeButtonTitle: TranslatedString
  hostName: string
  siteId: string
  userSettingsUrl: string
  agentReceiverPortIsDefault: boolean
}>()

const shellId = defineModel<string>('shellId', { default: '' })
const emit = defineEmits<{ close: [] }>()

const { _t } = usei18n()

const ott = ref<TokenValue>(null)
const collapsibleOpen = ref<boolean>(false)

const variants = computed<CommandChoice[] | null>(() =>
  props.spec.commands.kind === 'shell-variants' ? props.spec.commands.variants : null
)

const blocks = computed<CommandBlock[]>(() => {
  if (props.spec.commands.kind === 'single') {
    return [props.spec.commands.block]
  }
  const chosen = variants.value?.find((variant) => variant.id === shellId.value)
  return (chosen ?? variants.value?.[0])?.blocks ?? []
})

const rendered = computed(() => renderBlocks(blocks.value, 'registration', props.macros, ott.value))

/** The same commands without a token, for the registration-user fallback. */
const untokenised = computed(() => renderBlocks(blocks.value, 'registration', props.macros))

/** Whether the token command can be shown as it stands. */
const commandShown = computed(() => isResolved(rendered.value.tokenState))

/**
 * Registering with the agent_registration user is a legitimate way to finish
 * this step, so a failed token must not lock the user in - only a token that
 * has not been generated yet does.
 */
/** Whether the registration command needs a token at all. */
const needsToken = computed(() =>
  blocks.value.some((b) => requiresToken(b.command, 'registration'))
)

/**
 * Latches once a generation attempt failed. Retrying puts the token back to
 * `missing`, so without the latch the button would lock again while the
 * fallback command is still on screen.
 */
const generationFailed = ref(false)

const waitingForToken = computed(
  () => !generationFailed.value && rendered.value.tokenState === 'missing'
)

// A warning that points at the troubleshooting section is useless while that
// section is folded away.
watch(
  () => rendered.value.tokenState,
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
      <div v-if="isActive">
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
        <CmkAlertBox v-if="rendered.tokenState === 'failed'" variant="warning" size="small">
          {{
            _t(
              'The registration command is hidden until a token has been generated successfully. You can register with the agent_registration user instead - see "Troubleshooting registration issues" below.'
            )
          }}
        </CmkAlertBox>
        <template v-if="commandShown">
          <ShellToggle v-if="variants" v-model="shellId" :choices="variants" />
          <CmkParagraph>{{ spec.msg }}</CmkParagraph>
          <CommandBlockList :blocks="rendered.blocks" />
          <CmkAlertBox v-if="agentReceiverPortIsDefault" variant="warning" size="small">
            {{
              _t(
                'The agent receiver port could not be determined from the remote site. The command uses the default port (8000). Adjust the --server port if your site uses a different agent receiver port.'
              )
            }}
          </CmkAlertBox>
        </template>
      </div>
      <div v-else>
        <CmkParagraph>
          {{ _t('Run this command to register the Checkmk agent controller.') }}
        </CmkParagraph>
      </div>

      <template v-if="spec.troubleshooting === 'registration-user'">
        <CmkCollapsibleTitle
          :open="collapsibleOpen"
          :title="
            _t('Troubleshooting registration issues: Authenticate with the registration user')
          "
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
            <ShellToggle v-if="variants" v-model="shellId" :choices="variants" />
            <CommandBlockList :blocks="untokenised.blocks" />
          </CmkIndent>
        </CmkCollapsible>
      </template>
    </template>
    <template v-if="isActive" #actions>
      <CmkWizardButton
        v-if="isLastStep"
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
</style>
