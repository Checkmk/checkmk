<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import CmkAccordionStepPanelItem from 'cmk-ui-library/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkLinkCard from 'cmk-ui-library/components/CmkLinkCard'
import CmkWizard from 'cmk-ui-library/components/CmkWizard/CmkWizard.vue'
import CmkWizardButton from 'cmk-ui-library/components/CmkWizard/CmkWizardButton.vue'
import CmkWizardStep from 'cmk-ui-library/components/CmkWizard/CmkWizardStep.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import usePersistentRef from 'cmk-ui-library/lib/usePersistentRef'
import { type Ref, ref } from 'vue'

import StepCardsRow from '@/welcome/components/steps/components/StepCardsRow.vue'
import StepHeading from '@/welcome/components/steps/components/StepHeading.vue'
import StepParagraph from '@/welcome/components/steps/components/StepParagraph.vue'

import FirstHostSlideout from '../first-host/FirstHostSlideout.vue'
import type { StepId } from './utils'

const { _t, _tp } = usei18n()

const cseSlideoutOpen = ref<boolean>(false)

const props = defineProps<{
  step: number
  stepId: StepId
  cards: WelcomeCards
  accomplished: boolean
}>()

const useCseSlideout = ref<boolean>(false)
const currentStep: Ref<number> = usePersistentRef<number>(
  `${props.stepId}-currentStep`,
  0,
  (v) => v as number,
  'local'
)

if (props.cards.add_host === 'cse-first-host-slideout') {
  useCseSlideout.value = true
}

function openRelaySetup(): void {
  if (props.cards.relays) {
    window.location.href = props.cards.relays
  }
}

// One msgid for the whole sentence, so translations can move the link.
const relayNoteParts = _tp(
  '%{link} is the link text "Checkmk Relay"',
  'Systems behind a firewall? Set up a %{link} first.'
).split('%{link}')

const emit = defineEmits(['step-completed'])
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="step"
    :disabled="false"
    :accomplished="accomplished"
    :title="_t('Add your first host')"
    :info="_t('2 Steps | Takes 7-10 min')"
  >
    <StepParagraph>
      {{
        _t(
          `A host is anything you monitor: a server, a network device, a VM, a container platform,
a cloud account or an application. Checkmk finds its services automatically.`
        )
      }}
    </StepParagraph>

    <CmkWizard v-model="currentStep" mode="guided">
      <CmkWizardStep :index="0" :is-completed="() => currentStep > 0 || accomplished">
        <template #header>
          <CmkHeading type="h3">{{ _t('Add your first host') }}</CmkHeading>
        </template>
        <template #content>
          <div>
            <StepHeading>{{ _t('Servers & operating systems') }}</StepHeading>
            <StepCardsRow>
              <CmkLinkCard
                icon-name="folder"
                :url="useCseSlideout ? undefined : cards.add_host"
                :title="_t('Linux, Windows & Unix servers')"
                :subtitle="_t('Solaris, AIX, FreeBSD, macOS, ...')"
                :open-in-new-tab="false"
                :callback="
                  () => {
                    if (useCseSlideout) {
                      cseSlideoutOpen = true
                    }
                  }
                "
              />
            </StepCardsRow>
          </div>

          <CmkAlert
            v-if="useCseSlideout && cards.relays"
            variant="info"
            :heading="_t('Network devices and virtualization need a Checkmk Relay')"
            :text="
              _t(
                'Checkmk Cloud cannot reach systems inside your network directly. Set up a Checkmk Relay in your network first, then add network devices or virtualization platforms such as Proxmox VE.'
              )
            "
            :main-button="{ title: _t('Set up Checkmk Relay'), onclick: openRelaySetup }"
          />

          <div v-if="cards.network_devices">
            <StepHeading>{{ _t('Network devices') }}</StepHeading>
            <StepCardsRow>
              <CmkLinkCard
                icon-name="networking"
                :title="_t('Switches, routers, firewalls & other SNMP devices')"
                :url="cards.network_devices"
                :open-in-new-tab="false"
              />
            </StepCardsRow>
          </div>
          <StepParagraph
            v-if="!useCseSlideout && cards.relays"
            class="welcome-add-host__relay-note"
          >
            {{ relayNoteParts[0] }}<a :href="cards.relays">{{ _t('Checkmk Relay') }}</a
            >{{ relayNoteParts[1] }}
          </StepParagraph>

          <div>
            <StepHeading>{{ _t('Virtualization & containers') }}</StepHeading>
            <StepCardsRow>
              <CmkLinkCard
                icon-name="proxmox-ve"
                :title="_t('Proxmox VE')"
                :url="cards.proxmox_quick_setup"
                :open-in-new-tab="false"
              />
              <CmkLinkCard
                icon-name="kubernetes"
                :title="_t('Kubernetes')"
                :url="cards.kubernetes_quick_setup"
                :open-in-new-tab="false"
              />
            </StepCardsRow>
          </div>

          <div>
            <StepHeading>{{ _t('Cloud platforms') }}</StepHeading>
            <StepCardsRow>
              <CmkLinkCard
                icon-name="aws-logo"
                :title="_t('Amazon Web Services (AWS)')"
                :url="cards.aws_quick_setup"
                :open-in-new-tab="false"
              />
              <CmkLinkCard
                icon-name="azure-vms"
                :title="_t('Microsoft Azure')"
                :url="cards.azure_quick_setup"
                :open-in-new-tab="false"
              />
              <CmkLinkCard
                icon-name="gcp"
                :title="_t('Google Cloud Platform (GCP)')"
                :url="cards.gcp_quick_setup"
                :open-in-new-tab="false"
              />
            </StepCardsRow>
          </div>

          <div v-if="cards.synthetic_monitoring || cards.opentelemetry">
            <StepHeading>{{ _t('Applications & databases') }}</StepHeading>
            <StepCardsRow>
              <CmkLinkCard
                v-if="cards.synthetic_monitoring"
                icon-name="synthetic-monitoring-yellow"
                :title="_t('Synthetic monitoring')"
                :url="cards.synthetic_monitoring"
                :open-in-new-tab="false"
              />
              <CmkLinkCard
                v-if="cards.opentelemetry"
                icon-name="opentelemetry"
                :title="_t('OpenTelemetry (Beta)')"
                :url="cards.opentelemetry"
                :open-in-new-tab="false"
              />
            </StepCardsRow>
          </div>
        </template>
        <template #actions>
          <CmkWizardButton type="next" :override-label="_t('Continue')" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="1" :is-completed="() => currentStep > 1 || accomplished">
        <template #header>
          <CmkHeading type="h3">{{ _t('Activate changes') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              _t(
                `In Checkmk, configuration changes are first saved as pending and do not affect the running monitoring right away.
          This lets you prepare and review multiple changes — such as adding hosts, adjusting services, or fine-tuning
          thresholds — before applying them all at once. Only when you activate the pending changes are they transferred
          to the live monitoring system as a single bundle.`
              )
            }}
          </StepParagraph>
          <CmkAlert
            :heading="_t('Spotting pending changes')"
            :text="
              _t(
                `If there are pending changes, you’ll see a yellow badge on the “Changes” menu item in the main navigation, reminding you that your setup is not yet active.`
              )
            "
          />

          <StepCardsRow>
            <CmkLinkCard
              icon-name="main-changes"
              :title="_t('Open all pending changes')"
              :url="cards.activate_changes"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
        <template #actions>
          <CmkWizardButton
            v-if="!accomplished && step"
            type="finish"
            :override-label="_t('Mark as done')"
            @click="emit('step-completed', stepId)"
          />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </CmkAccordionStepPanelItem>

  <FirstHostSlideout v-if="useCseSlideout" v-model="cseSlideoutOpen" />
</template>

<style scoped>
.welcome-add-host__relay-note {
  margin-top: var(--spacing);
}
</style>
