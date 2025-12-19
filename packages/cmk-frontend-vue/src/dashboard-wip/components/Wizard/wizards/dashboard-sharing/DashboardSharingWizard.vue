<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkSlideIn from '@/components/CmkSlideIn.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import type { DashboardFeatures, DashboardKey } from '@/dashboard-wip/types/dashboard'

import ActionBar from '../../components/ActionBar.vue'
import ActionButton from '../../components/ActionButton.vue'
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
    <Suspense>
      <WizardStageContainer>
        <CmkHeading type="h1">
          {{ _t('Configure sharing') }}
        </CmkHeading>
        <CloseButton @close="() => $emit('close')" />

        <ContentSpacer />

        <ActionBar align-items="left">
          <ActionButton :label="_t('Close')" :action="() => $emit('close')" variant="secondary" />
        </ActionBar>

        <ContentSpacer />

        <InternalAccess :dashboard-url="dashboardUrl" />

        <ContentSpacer />

        <PublicAccess
          :dashboard-key="dashboardKey"
          :public-token="clonedToken"
          :available-features="availableFeatures"
          @refresh-dashboard-settings="$emit('refreshDashboardSettings')"
        />
      </WizardStageContainer>
    </Suspense>
    <template #fallback>
      <CmkIcon name="load-graph" size="xxlarge" />
    </template>
  </CmkSlideIn>
</template>

<style scoped>
.db-sharing-wizard__root {
  height: 95vh;
  overflow-y: auto;
  display: flex;
}

.db-sharing-wizard__container {
  width: 100vh;
  flex: 2;
  padding: var(--spacing-double);
}

.db-sharing-wizard__box {
  background-color: var(--ux-theme-2);
}
</style>
