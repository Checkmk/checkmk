<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkSlideIn from '@/components/CmkSlideIn.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import type { DashboardFeatures, DashboardKey } from '@/dashboard/types/dashboard'

import ActionBar from '../../components/ActionBar.vue'
import CloseButton from '../../components/CloseButton.vue'
import ContentSpacer from '../../components/ContentSpacer.vue'
import WizardStageContainer from '../../components/WizardStageContainer.vue'
import InternalAccess from './InternalAccess.vue'
import PublicAccess from './PublicAccess.vue'
import type { DashboardTokenModel } from './api'

const { _t } = usei18n()

interface ShareDashboardSettingsProps {
  dashboardKey: DashboardKey
  publicToken: DashboardTokenModel | null
  availableFeatures: DashboardFeatures
}

interface ShareDashboardSettingsEmits {
  close: []
  refreshDashboardSettings: []
}

const props = defineProps<ShareDashboardSettingsProps>()
defineEmits<ShareDashboardSettingsEmits>()

const dashboardUrl = computed(() => window?.parent?.location?.href || window.location.href)
const clonedToken = computed(() => (props.publicToken ? structuredClone(props.publicToken) : null))
</script>

<template>
  <CmkSlideIn :open="true" size="small">
    <WizardStageContainer>
      <CmkHeading type="h1">
        {{ _t('Configure sharing') }}
      </CmkHeading>
      <CloseButton @close="() => $emit('close')" />

      <ContentSpacer />

      <ActionBar align-items="left">
        <CmkButton variant="optional" @click="$emit('close')">
          {{ _t('Close') }}
        </CmkButton>
      </ActionBar>

      <InternalAccess class="db-sharing-wizard__internal-access" :dashboard-url="dashboardUrl" />

      <PublicAccess
        :dashboard-key="dashboardKey"
        :public-token="clonedToken"
        :available-features="availableFeatures"
        @refresh-dashboard-settings="$emit('refreshDashboardSettings')"
      />
    </WizardStageContainer>
  </CmkSlideIn>
</template>

<style scoped>
.db-sharing-wizard__internal-access {
  margin-top: var(--dimension-11);
  margin-bottom: var(--dimension-8);
}
</style>
