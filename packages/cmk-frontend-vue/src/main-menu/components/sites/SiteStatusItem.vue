<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkBadge from '@/components/CmkBadge.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkProgressbar from '@/components/CmkProgressbar.vue'
import CmkZebra from '@/components/CmkZebra.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import type { Site } from '../../ChangesInterfaces'

const { _t } = usei18n()

const statusColor = (status: string): 'success' | 'warning' | 'danger' | 'default' => {
  const mapping: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
    online: 'success',
    disabled: 'warning',
    down: 'danger',
    unknown: 'default',
    unreach: 'danger',
    dead: 'danger',
    waiting: 'warning',
    missing: 'warning'
  }
  return mapping[status] ?? 'warning'
}

defineProps<{
  site: Site
  idx: number
  activating: boolean
  checked: boolean
  isRecentlyActivated: boolean
  hideCheckbox?: boolean
}>()

const emit = defineEmits<{
  updateChecked: [string, boolean]
}>()
</script>

<template>
  <CmkZebra :num="idx" class="cmk-changes-sites-item-wrapper">
    <div class="cmk-changes-sites-item">
      <div class="cmk-changes-sites-item-start">
        <CmkCheckbox
          v-if="!hideCheckbox"
          :model-value="checked"
          :disabled="site.onlineStatus !== 'online'"
          @update:model-value="
            (val) => {
              emit('updateChecked', site.siteId, val)
            }
          "
        />
        <CmkBadge :color="statusColor(site.onlineStatus)" size="small">{{
          site.onlineStatus
        }}</CmkBadge>
        <div class="cmk-changes-sites-item-name">{{ site.siteName }}</div>
      </div>
      <div
        v-if="site.changes > 0 && !activating && !isRecentlyActivated"
        class="cmk-changes-sites-item-end"
      >
        <span class="cmk-span-changes-text">{{ _t('Changes:') }}</span>
        <CmkBadge color="warning" size="small">{{ site.changes }}</CmkBadge>
      </div>
      <div
        v-if="site.changes === 0 && !activating && !isRecentlyActivated"
        class="cmk-changes-sites-item-end"
      >
        <span class="cmk-span-changes-text">{{ _t('No changes') }}</span>
      </div>
      <div
        v-if="isRecentlyActivated && site.lastActivationStatus !== undefined"
        class="cmk-changes-sites-item-end"
      >
        <div>
          {{ site.lastActivationStatus.status_text }}
        </div>
      </div>
      <div v-if="activating && !isRecentlyActivated && checked" class="cmk-changes-sites-item-end">
        <div class="cmk-progress-bar-site-activation-in-progress">
          <CmkProgressbar max="unknown"></CmkProgressbar>
        </div>
      </div>
    </div>
    <div
      v-if="hideCheckbox && site.lastActivationStatus?.state === 'warning'"
      class="cmk-div-site-activate-warning"
    >
      <CmkIcon variant="inline" name="validation-error" />
      <div class="cmk-div-warning-or-error-message">
        <span v-if="site.lastActivationStatus?.state === 'warning'">{{ _t('Warning') }}</span>
        <span class="grey-text">{{ site.lastActivationStatus.status_details }}</span>
      </div>
    </div>
    <div
      v-if="hideCheckbox && site.lastActivationStatus?.state === 'error'"
      class="cmk-div-site-activate-error"
    >
      <CmkIcon variant="inline" name="alert_crit" />
      <div class="cmk-div-warning-or-error-message">
        <span v-if="site.lastActivationStatus.state === 'error'">{{ _t('Error') }}</span>
        <span class="grey-text">{{ site.lastActivationStatus.status_details }}</span>
      </div>
    </div>
  </CmkZebra>
</template>

<style scoped>
.cmk-changes-sites-item-wrapper {
  background: var(--default-bg-color);
  padding: var(--dimension-3);
  box-sizing: border-box;
}

.cmk-changes-sites-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;

  .cmk-changes-sites-item-start {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: var(--spacing-half);

    .cmk-changes-sites-item-name {
      text-overflow: ellipsis;
      overflow: hidden;
      max-width: 250px;
      white-space: nowrap;
    }
  }

  .cmk-changes-sites-item-end {
    display: flex;
    flex-direction: row;
    align-items: center;
  }

  .cmk-span-changes-text {
    color: var(--font-color-dimmed);
    font-size: var(--font-size-normal);
    font-weight: var(--font-weight-default);
  }
}

.cmk-progress-bar-site-activation-in-progress {
  width: 150px;
}

.cmk-div-site-activate-error {
  background: rgb(234 57 8 / 15%);
}

.cmk-div-site-activate-warning {
  background: rgb(255 202 40 / 15%); /* TODO: add var */
}

.cmk-div-site-activate-warning,
.cmk-div-site-activate-error {
  display: flex;
  padding: var(--dimension-2) var(--dimension-4);
  justify-content: left;
  align-items: center;
  gap: var(--dimension-3);
  align-self: stretch;
  border-radius: var(--border-radius);
  margin: 0 var(--dimension-3);
}

.cmk-div-warning-or-error-message {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  padding: var(--dimension-3) 0;
  font-weight: var(--font-weight-bold);
}

.grey-text {
  color: var(--font-color-dimmed);
  font-weight: var(--font-weight-default);
}

.red-text {
  color: var(--color-danger);
}
</style>
