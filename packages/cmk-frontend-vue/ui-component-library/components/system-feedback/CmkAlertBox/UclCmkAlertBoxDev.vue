<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'
import { useDismissDialog } from '@/lib/useDismissDialog'

import CmkAlertBox from '@/components/CmkAlertBox.vue'

defineProps<{ screenshotMode: boolean }>()

const { _t } = usei18n()

const { isShown: mode1Shown, dismiss: dismissMode1 } = useDismissDialog('ucl_cmk_alert_box_demo')
function resetMode1() {
  mode1Shown.value = true
}

const autoDismissOpen = ref(true)

function reset() {
  autoDismissOpen.value = true
}
</script>

<template>
  <div>
    <section>
      <h3>Mode 1: With buttons</h3>
      <p>
        Headline + body required. No close icon. Dismissed via buttons only.
        <button v-if="!mode1Shown" type="button" @click="resetMode1">Reset</button>
      </p>
      <template v-if="mode1Shown">
        <CmkAlertBox
          v-for="v in ['info', 'success', 'warning', 'error'] as const"
          :key="v"
          :variant="v"
          heading="Headline"
          :main-button="{ title: _t('Confirm'), onclick: () => {} }"
          :buttons="[
            { title: _t('Edit'), variant: 'secondary', onclick: () => {} },
            { title: _t('Dismiss'), variant: 'optional', onclick: dismissMode1 }
          ]"
        >
          Body text to provide context.
        </CmkAlertBox>
      </template>
    </section>

    <section>
      <h3>Mode 2: Without buttons, dismissible</h3>
      <p>Optional close icon. Dismissed on page reload.</p>
      <CmkAlertBox
        v-for="v in ['info', 'success'] as const"
        :key="v"
        :variant="v"
        heading="Headline"
        :dismissible="true"
      >
        Body text to provide context.
      </CmkAlertBox>
    </section>

    <section>
      <h3>Mode 2b: Without buttons, not dismissible</h3>
      <p>No close icon. Alert stays visible until the surrounding context changes.</p>
      <CmkAlertBox
        v-for="v in ['warning', 'error', 'loading'] as const"
        :key="v"
        :variant="v"
        heading="Headline"
      >
        Body text to provide context.
      </CmkAlertBox>
    </section>

    <section>
      <h3>Mode 3: Auto-dismiss (success only)</h3>
      <p>
        Dismissed automatically after 6 seconds.
        <button type="button" @click="reset">Reset</button>
      </p>
      <CmkAlertBox
        v-model:open="autoDismissOpen"
        variant="success"
        heading="Operation completed"
        :auto-dismiss="true"
      >
        This alert will dismiss automatically after 6 seconds.
      </CmkAlertBox>
    </section>

    <section>
      <h3>Sizes</h3>
      <CmkAlertBox variant="info" heading="Medium (default)">This is the medium size.</CmkAlertBox>
      <CmkAlertBox variant="info" size="small">This is the small size.</CmkAlertBox>
    </section>

    <section>
      <h3>Responsive behavior</h3>
      <p>Global — full container width</p>
      <CmkAlertBox variant="info" heading="This is a headline">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut
        labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco
        laboris nisi ut aliquip ex ea commodo consequat.
      </CmkAlertBox>
      <p>Contextual — narrow placement (~280px)</p>
      <div class="ucl-cmk-alert-box-dev__contextual">
        <CmkAlertBox
          variant="info"
          heading="This is a very long headline to test the responsive behavior of the alert box in a narrow container"
        >
          Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt
          ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation
          ullamco laboris nisi ut aliquip ex ea commodo consequat.
        </CmkAlertBox>
      </div>
    </section>
  </div>
</template>

<style scoped>
.ucl-cmk-alert-box-dev__contextual {
  max-width: 280px;
}
</style>
