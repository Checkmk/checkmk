<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import { type Ref, ref } from 'vue'

import usei18n from '@/lib/i18n'
import usePersistentRef from '@/lib/usePersistentRef'

import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import CmkLinkCard from '@/components/CmkLinkCard'
import CmkWizard from '@/components/CmkWizard/CmkWizard.vue'
import CmkWizardButton from '@/components/CmkWizard/CmkWizardButton.vue'
import CmkWizardStep from '@/components/CmkWizard/CmkWizardStep.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import StepCardsRow from '@/welcome/components/steps/components/StepCardsRow.vue'
import StepHeading from '@/welcome/components/steps/components/StepHeading.vue'
import StepParagraph from '@/welcome/components/steps/components/StepParagraph.vue'

import FirstHostSlideout from '../first-host/FirstHostSlideout.vue'

const { _t } = usei18n()

const cseSlideoutOpen = ref<boolean>(false)

const props = defineProps<{
  step: number
  cards: WelcomeCards
  accomplished: boolean
}>()

const useCseSlideout = ref<boolean>(false)
const currentStep: Ref<number> = usePersistentRef<number>(
  `${props.step}-currentStep`,
  0,
  (v) => v as number,
  'local'
)

if (props.cards.add_host === 'cse-first-host-slideout') {
  useCseSlideout.value = true
}
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="step"
    :disabled="false"
    :accomplished="accomplished"
    :title="_t('Add your first host')"
    :info="_t('2-5 min')"
  >
    <StepParagraph>
      {{
        _t(
          `In Checkmk, a host is any standalone physical or virtual system that is monitored.
Each host has services which represent what is monitored, for example CPU usage, disk space, processes, or hardware sensors.
The service discovery of Checkmk automatically detects these services.
This allows monitoring to start with minimal configuration effort.`
        )
      }}
    </StepParagraph>

    <CmkWizard v-model="currentStep" mode="guided">
      <CmkWizardStep :index="0" :is-completed="() => currentStep >= 0">
        <template #header>
          <CmkHeading type="h3">{{ _t('Open and run service discovery') }}</CmkHeading>
        </template>
        <template #content>
          <StepHeading>
            {{ _t('On-premises hosts') }}
          </StepHeading>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="folder"
              :url="useCseSlideout ? undefined : cards.add_host"
              :title="_t('Server (Linux, Windows, Solaris, ...)')"
              :open-in-new-tab="false"
              :callback="
                () => {
                  if (useCseSlideout) {
                    cseSlideoutOpen = true
                  }
                }
              "
            />
            <CmkLinkCard
              icon-name="networking"
              :title="_t('Network devices and SNMP')"
              :url="cards.network_devices"
              :open-in-new-tab="false"
            />
          </StepCardsRow>

          <StepHeading>
            {{ _t('Cloud hosts') }}
          </StepHeading>
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

          <template v-if="cards.synthetic_monitoring || cards.opentelemetry">
            <StepHeading>
              {{ _t('Application monitoring') }}
            </StepHeading>
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
          </template>
        </template>
        <template #actions>
          <CmkWizardButton type="next" :override-label="_t('Continue')" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="1" :is-completed="() => currentStep >= 1">
        <template #header>
          <CmkHeading type="h3">{{ _t('Activate changes') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              _t(
                `Changes are saved in a temporary environment first,
                letting you review and adjust them safely.`
              )
            }}
            <br />
            {{ _t('Activate changes to apply them to live monitoring.') }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="main-changes"
              :title="_t('Activate changes')"
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
          />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </CmkAccordionStepPanelItem>

  <FirstHostSlideout v-if="useCseSlideout" v-model="cseSlideoutOpen" />
</template>
