<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import { useTeleportPlacement } from '@/monitoring/shared/components/teleportPlacement'

const { _t } = usei18n()

const props = defineProps<{ url: string; teleportTarget?: string | null | undefined }>()

const { target, isDefault } = useTeleportPlacement('.titlebar', () => props.teleportTarget)
</script>

<template>
  <Teleport defer :to="target">
    <CmkLink
      :href="url"
      target="_blank"
      class="monitoring-survey-link"
      :class="isDefault ? 'monitoring-survey-link--titlebar' : 'monitoring-survey-link--inline'"
    >
      <CmkIcon name="comment" class="monitoring-survey-link__icon" />
      {{ _t('Give feedback on the new view') }}
    </CmkLink>
  </Teleport>
</template>

<style scoped>
.monitoring-survey-link--titlebar {
  margin-right: var(--dimension-6);
  place-content: center flex-end;
  align-items: center;
}

.monitoring-survey-link--inline {
  margin-left: var(--dimension-4);
  vertical-align: middle;
}

.monitoring-survey-link__icon {
  margin-right: var(--dimension-3);
}
</style>
