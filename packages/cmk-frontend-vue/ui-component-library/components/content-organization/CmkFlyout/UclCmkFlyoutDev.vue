<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'

import { untranslated } from '@/lib/i18n'

import CmkButton from '@/components/CmkButton'
import CmkFlyout from '@/components/CmkFlyout'

defineProps<{ screenshotMode: boolean }>()

const plainOpen = ref(false)
const triggerRef = useTemplateRef<InstanceType<typeof CmkButton>>('triggerRef')
</script>

<template>
  <ul>
    <li>
      Plain flyout (content only, closes on outside click or Escape):
      <CmkFlyout
        :open="plainOpen"
        :label="untranslated('Plain flyout')"
        :restore-focus="() => triggerRef?.focus()"
        @cancel="plainOpen = false"
      >
        <template #trigger="{ aria }">
          <CmkButton ref="triggerRef" v-bind="aria" @click="plainOpen = !plainOpen"
            >Plain</CmkButton
          >
        </template>
        <p>Just some popup content.</p>
      </CmkFlyout>
    </li>
  </ul>
  <div class="ucl-cmk-flyout-dev__placeholder">
    Placeholder content so we don't cut off the flyout with the collapsible.
  </div>
</template>

<style scoped>
.ucl-cmk-flyout-dev__placeholder {
  height: 40px;
}
</style>
