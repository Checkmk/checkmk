<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useLegacyCss } from '@ucl/_ucl/composables/useLegacyCss'

import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkSwitch from '@/components/CmkSwitch.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

const { isLegacyCssEnabled } = useLegacyCss()
</script>

<template>
  <div class="ucl-legacy-css-switch">
    <CmkHeading type="h4">Legacy CSS</CmkHeading>

    <CmkHelpText
      help="When enabled, legacy CSS styling is active. When disabled, only the Vue-based styling is applied. The component should render correctly and maintain a consistent, polished appearance in both modes."
      aria-label="Legacy CSS help"
    />
    <CmkSpace size="small" />

    <CmkSwitch v-model:data="isLegacyCssEnabled" />
  </div>
</template>

<style scoped>
.ucl-legacy-css-switch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid var(--ucl-elements-border-color);
  border-radius: var(--border-radius);
}
</style>
