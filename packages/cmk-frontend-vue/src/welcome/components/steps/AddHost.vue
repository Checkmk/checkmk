<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import CmkLinkCard from '@/components/CmkLinkCard'

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
          `Each host includes a number of services that represent what you want to monitor, for example,
  CPU usage, disk space, running processes, or hardware sensors. Checkmk makes this easy with the
  Service Discovery, which automatically detects relevant services on your host, so you can start
  monitoring with minimal setup.`
        )
      }}
    </StepParagraph>

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
  </CmkAccordionStepPanelItem>

  <FirstHostSlideout v-if="useCseSlideout" v-model="cseSlideoutOpen" />
</template>
