<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkCode from 'cmk-ui-library/components/CmkCode.vue'
import CmkLinkCard from 'cmk-ui-library/components/CmkLinkCard'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import { CmkWizardButton } from 'cmk-ui-library/components/CmkWizard'
import CmkWizardStep from 'cmk-ui-library/components/CmkWizard/CmkWizardStep.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import { applyToken, isResolved, requiresToken } from '../../lib/commandTemplate'
import type { AgentSlideOutTabs } from '../../lib/type_def'
import GenerateToken from '../GenerateToken.vue'

const props = defineProps<{
  index: number
  isCompleted: () => boolean
  isActive: boolean
  tab: AgentSlideOutTabs
  siteId: string
}>()

/** The agent download token. */
const ott = defineModel<string | null | Error>('ott', { required: true })
/** The selected shell (PowerShell/Command Prompt). */
const selectedVariantId = defineModel<string>('selectedVariantId', { default: '' })
/** The selected package (DEB/RPM/TGZ). */
const packageId = defineModel<string>('packageId', { default: '' })

const { _t } = usei18n()

const activeSubTab = computed(() => props.tab.subTabs?.find((st) => st.id === packageId.value))

/**
 * The install commands on screen, branching exactly like the template below so
 * that a command it never renders cannot influence the token handling.
 */
const currentCmds = computed<string[]>(() => {
  const variants = props.tab.installCmdVariants
  const cmds: (string | undefined)[] = []
  if (variants && variants.length > 1) {
    const variant = variants.find((v) => v.id === selectedVariantId.value)
    cmds.push(variant?.downloadCmd, variant?.installCmd)
  } else if (props.tab.installDownloadCmd) {
    cmds.push(props.tab.installDownloadCmd, props.tab.installCmd)
  } else if (props.tab.installMsg && props.tab.installCmd) {
    cmds.push(props.tab.installCmd)
  }
  cmds.push(activeSubTab.value?.downloadCmd, activeSubTab.value?.installCmd)
  return cmds.filter((cmd): cmd is string => !!cmd)
})

/** Whether any command on screen cannot be run without a token. */
const needsToken = computed(() => currentCmds.value.some((cmd) => requiresToken(cmd, 'download')))

const installMsg = computed(() => {
  if (props.tab.subTabs) {
    return activeSubTab.value?.installMsg || props.tab.installMsg || ''
  }
  return props.tab.installMsg || ''
})

function cmdWithToken(cmd: string | undefined): string {
  return applyToken(cmd, 'download', ott.value).text
}

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
const cmdsResolved = computed(() =>
  currentCmds.value.every((cmd) => isResolved(applyToken(cmd, 'download', ott.value).tokenState))
)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading> {{ _t('Download and install') }}</CmkHeading>
    </template>
    <template #content>
      <div v-if="isActive" class="download_install__content">
        <template v-if="currentCmds.length > 0 && !tab.unbakedFallback">
          <div class="download_install__token">
            <CmkParagraph>{{ installMsg }}</CmkParagraph>
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
          <template v-if="cmdsResolved">
            <template v-if="tab.installCmdVariants && tab.installCmdVariants.length > 1">
              <CmkToggleButtonGroup
                v-model="selectedVariantId"
                class="shell-toggle"
                :options="tab.installCmdVariants.map((v) => ({ label: v.label, value: v.id }))"
              />
              <template v-for="variant in tab.installCmdVariants" :key="variant.id">
                <template v-if="variant.id === selectedVariantId">
                  <CmkCode
                    :title="_t('Download the agent')"
                    :code-text="cmdWithToken(variant.downloadCmd || '')"
                    class="code"
                    width="fill"
                  />
                  <CmkAlertBox v-if="tab.installWarning" variant="warning">
                    {{ tab.installWarning }}
                  </CmkAlertBox>
                  <CmkCode
                    :title="_t('Install the agent')"
                    :code-text="variant.installCmd"
                    class="code"
                    width="fill"
                  />
                </template>
              </template>
            </template>
            <template v-else-if="tab.installDownloadCmd">
              <CmkCode
                :title="_t('Download the agent')"
                :code-text="cmdWithToken(tab.installDownloadCmd)"
                class="code"
                width="fill"
              />
              <CmkAlertBox v-if="tab.installWarning" variant="warning">
                {{ tab.installWarning }}
              </CmkAlertBox>
              <CmkCode
                :title="_t('Install the agent')"
                :code-text="tab.installCmd || ''"
                class="code"
                width="fill"
              />
            </template>
            <CmkCode
              v-else-if="tab.installMsg && tab.installCmd"
              :code-text="cmdWithToken(tab.installCmd)"
              class="code"
              width="fill"
            />
            <template v-if="activeSubTab">
              <template v-if="activeSubTab.downloadCmd">
                <CmkCode
                  :title="_t('Download the agent')"
                  :code-text="cmdWithToken(activeSubTab.downloadCmd)"
                  class="code"
                  width="fill"
                />
                <CmkAlertBox v-if="activeSubTab.installWarning" variant="warning">
                  {{ activeSubTab.installWarning }}
                </CmkAlertBox>
                <CmkCode
                  :title="_t('Install the agent')"
                  :code-text="activeSubTab.installCmd"
                  class="code"
                  width="fill"
                />
              </template>
              <CmkCode
                v-else
                :code-text="cmdWithToken(activeSubTab.installCmd)"
                class="code"
                width="fill"
              />
            </template>
          </template>
        </template>
        <template v-else-if="tab.unbakedFallback">
          <CmkAlertBox variant="warning">
            {{ tab.unbakedFallback.intro }}
          </CmkAlertBox>
          <CmkCode
            v-for="cmd in tab.unbakedFallback.commands"
            :key="cmd"
            :code-text="cmd"
            class="code"
            width="fill"
          />
        </template>
        <div v-else-if="tab.installUrl" class="install_url__div">
          <CmkParagraph v-if="tab.installUrl.msg">{{ tab.installUrl.msg }}</CmkParagraph>
          <CmkLinkCard
            :title="tab.installUrl.title"
            :url="tab.installUrl.url"
            :icon-name="tab.installUrl.icon"
            :open-in-new-tab="true"
          />
        </div>
      </div>
    </template>
    <template v-if="isActive" #actions>
      <CmkWizardButton
        type="next"
        :disabled="!tab.unbakedFallback && !downloadFailed && !cmdsResolved"
        :override-label="_t('Next step: Register agent')"
      />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.code {
  margin: var(--dimension-5) 0 var(--dimension-7);
  width: 100%;
}

.shell-toggle {
  margin-top: var(--dimension-5);
  margin-bottom: var(--dimension-5);
}

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
