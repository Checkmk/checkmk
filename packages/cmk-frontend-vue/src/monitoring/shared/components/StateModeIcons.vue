<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The icons beside a state tag, always in this order: stale, flapping, then the state modes
(acknowledged, downtime, comments) a caller picked with stateModes(). A mode with a view of
its own links to it. Shared so the State column and the slide-in headers render the same.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import CmkIconLink from 'cmk-ui-library/components/CmkIconLink.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { MonitoringIcon } from '../api/types'

defineProps<{
  flapping?: boolean | undefined
  stale?: boolean | undefined
  modes?: readonly MonitoringIcon[] | undefined
}>()

const { _t } = usei18n()
</script>

<template>
  <span v-if="stale" class="monitoring-state-mode-icons__item">
    <CmkMultitoneIcon
      class="monitoring-state-mode-icons__icon"
      name="stale"
      primary-color="font"
      :title="_t('Stale')"
      :aria-label="_t('Stale')"
    />
  </span>
  <span v-if="flapping" class="monitoring-state-mode-icons__item">
    <CmkIcon class="monitoring-state-mode-icons__icon" name="flapping" :title="_t('Flapping')" />
  </span>
  <template v-for="mode in modes ?? []" :key="mode.icon_name">
    <CmkIconLink
      v-if="mode.link"
      class="monitoring-state-mode-icons__link"
      :name="mode.icon_name as SimpleIcons"
      :title="mode.title"
      :href="mode.link"
      target="_top"
      size="medium"
    />
    <span v-else class="monitoring-state-mode-icons__item">
      <CmkIcon
        class="monitoring-state-mode-icons__icon"
        :name="mode.icon_name as SimpleIcons"
        :title="mode.title"
        size="medium"
      />
    </span>
  </template>
</template>

<style scoped>
/* A 16 px icon in a 20 px box: a link shows its hover background in that box. */
.monitoring-state-mode-icons__item {
  display: inline-flex;
  flex: 0 0 auto;
  padding: var(--dimension-2);
}

.monitoring-state-mode-icons__icon {
  width: var(--dimension-6);
  height: var(--dimension-6);
}

.monitoring-state-mode-icons__link {
  flex: 0 0 auto;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.monitoring-state-mode-icons__link :deep(.cmk-icon) {
  width: var(--dimension-6);
  height: var(--dimension-6);
}
</style>
