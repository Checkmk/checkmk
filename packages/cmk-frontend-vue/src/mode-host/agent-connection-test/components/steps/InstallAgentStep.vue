<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkLinkCard from 'cmk-ui-library/components/CmkLinkCard'
import { CmkWizardButton } from 'cmk-ui-library/components/CmkWizard'
import CmkWizardStep from 'cmk-ui-library/components/CmkWizard/CmkWizardStep.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import {
  type HostMacros,
  type TokenValue,
  blocksNeedToken,
  isResolved,
  renderBlocks
} from '../../lib/commandTemplate'
import type { CommandBlock, CommandChoice, InstallSpec } from '../../lib/types'
import CommandBlockList from '../CommandBlockList.vue'
import GenerateToken from '../GenerateToken.vue'
import ShellToggle from '../ShellToggle.vue'

const props = defineProps<{
  index: number
  isCompleted: () => boolean
  isActive: boolean
  spec: InstallSpec
  macros: HostMacros
  siteId: string
}>()

/** The agent download token. */
const ott = defineModel<TokenValue>('ott', { required: true })
/** The selected shell (PowerShell/Command Prompt). */
const shellId = defineModel<string>('shellId', { default: '' })
/** The selected package (DEB/RPM/TGZ). */
const packageId = defineModel<string>('packageId', { default: '' })

const { _t } = usei18n()

function pick(choices: CommandChoice[], id: string): CommandChoice {
  return choices.find((choice) => choice.id === id) ?? choices[0]!
}

/** The choice the toggle currently selects, if this spec has one. */
const choice = computed<CommandChoice | null>(() => {
  switch (props.spec.kind) {
    case 'shell-variants':
      return pick(props.spec.variants, shellId.value)
    case 'package-choice':
      return pick(props.spec.choices, packageId.value)
    default:
      return null
  }
})

const blocks = computed<CommandBlock[]>(() => {
  if (choice.value !== null) {
    return choice.value.blocks
  }
  return props.spec.kind === 'commands' || props.spec.kind === 'unbaked-fallback'
    ? props.spec.blocks
    : []
})

/** The text above the commands, which the package choice may override. */
const intro = computed(() => {
  if (props.spec.kind === 'package-choice') {
    return choice.value?.intro ?? ''
  }
  return props.spec.kind === 'external-doc' ? props.spec.msg : props.spec.intro
})

const needsToken = computed(() => blocksNeedToken(blocks.value, 'download'))
const rendered = computed(() => renderBlocks(blocks.value, 'download', props.macros, ott.value))

/**
 * Latches once a token generation attempt failed. The agents page in the
 * header is the manual way to get the package, so a failed token must not
 * block the step - only a token nobody has tried to generate yet does.
 */
const downloadFailed = ref(false)
watch(ott, (value) => {
  if (value instanceof Error) {
    downloadFailed.value = true
  }
})

// Another package is a fresh context: nothing has been attempted for it, so
// the latch must not carry over. Platforms cannot carry it over either - each
// one renders its own instance of this step.
watch(packageId, () => {
  downloadFailed.value = false
})

/** True when every command on screen can be shown as it stands. */
const cmdsResolved = computed(() => isResolved(rendered.value.tokenState))
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading> {{ _t('Download and install') }}</CmkHeading>
    </template>
    <template #content>
      <div v-if="isActive" class="download_install__content">
        <div v-if="spec.kind === 'external-doc'" class="install_url__div">
          <CmkParagraph>{{ spec.msg }}</CmkParagraph>
          <CmkLinkCard
            :title="spec.link.title"
            :url="spec.link.url"
            :icon-name="spec.link.icon"
            :open-in-new-tab="true"
          />
        </div>
        <template v-else>
          <CmkAlertBox v-if="spec.kind === 'unbaked-fallback'" variant="warning">
            {{ spec.intro }}
          </CmkAlertBox>
          <div v-else class="download_install__token">
            <CmkParagraph>{{ intro }}</CmkParagraph>
            <GenerateToken
              v-if="needsToken"
              v-model="ott"
              token-generation-endpoint-uri="domain-types/agent_download_token/collections/all"
              :description="
                _t(
                  'To securely fetch the latest agent package via the command line, you must first generate a temporary authentication token. ' +
                    'This token is valid for 7 days and is used solely for the download process'
                )
              "
              :expires-in-seconds="604800"
              :token-generation-body="{ site_id: siteId }"
            />
          </div>
          <ShellToggle
            v-if="spec.kind === 'shell-variants' && cmdsResolved"
            v-model="shellId"
            :choices="spec.variants"
          />
          <CommandBlockList v-if="cmdsResolved" :blocks="rendered.blocks" />
        </template>
      </div>
    </template>
    <template v-if="isActive" #actions>
      <CmkWizardButton
        type="next"
        :disabled="!downloadFailed && !cmdsResolved"
        :override-label="_t('Next step: Register agent')"
      />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.install_url__div {
  margin-bottom: var(--spacing);
}

.download_install__content {
  width: 100%;
}

.download_install__token {
  width: 100%;
}
</style>
