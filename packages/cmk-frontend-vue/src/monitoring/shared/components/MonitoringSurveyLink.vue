<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineProps<{ url: string }>()
</script>

<template>
  <CmkLink
    :href="url"
    target="_blank"
    class="monitoring-survey-link"
    :title="_t('Give feedback on the new view')"
  >
    <CmkIcon name="comment" class="monitoring-survey-link__icon" />
    <span class="monitoring-survey-link__label">{{ _t('Give feedback on the new view') }}</span>
  </CmkLink>
</template>

<style scoped lang="scss">
@use '@/assets/breakpoints' as bp;

.monitoring-survey-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  width: auto;
}

.monitoring-survey-link__icon {
  margin-right: var(--dimension-3);
}

/* The reference is the title row (the container set by MonitoringHeaderActions), not the
   viewport, as the sidebar narrows it. Outside of it (page menu) the full label stays.
   Feedback is secondary to working with the view, so below L only the icon stays and
   the title/breadcrumb get the room; the label remains as tooltip and for assistive technology. */
@include bp.container-below(l) {
  .monitoring-survey-link__label {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }

  .monitoring-survey-link__icon {
    margin-right: 0;
  }
}
</style>
