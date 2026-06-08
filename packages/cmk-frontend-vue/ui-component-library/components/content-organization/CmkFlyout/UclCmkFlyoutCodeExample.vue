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

const open = ref(false)
const triggerRef = useTemplateRef<InstanceType<typeof CmkButton>>('triggerRef')
</script>

<template>
  <!-- CmkFlyout is fully controlled: the owner holds `open`, drives it from the trigger, and
       closes on the `cancel` event (Escape / outside press / focus leaving). -->
  <CmkFlyout
    :open="open"
    :label="untranslated('Example flyout')"
    :restore-focus="() => triggerRef?.focus()"
    @cancel="open = false"
  >
    <!-- Bind `aria` onto the focusable trigger so screen readers announce the popup. `restoreFocus`
         returns focus there when the popup closes with focus inside it. -->
    <template #trigger="{ aria }">
      <CmkButton ref="triggerRef" v-bind="aria" @click="open = !open">Open flyout</CmkButton>
    </template>

    <p>Any content can live inside the flyout popup.</p>
  </CmkFlyout>
</template>
