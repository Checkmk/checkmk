<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useDismissDialog } from 'cmk-ui-library/lib/useDismissDialog'
import { ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const { _t } = usei18n()

// This demo key is deliberately not one of the warnings the server knows, so
// the dismissal it sends is a no-op the backend rejects. A real key would
// dismiss that warning in the user config of whoever opens the library.
// @ts-expect-error demo-only key, not a DismissableWarning
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
        <CmkAlert
          v-for="v in ['info', 'success', 'warning', 'error'] as const"
          :key="v"
          :variant="v"
          heading="Headline"
          :main-button="{ title: _t('Confirm'), onclick: () => {} }"
          :optional-button="{ title: _t('Dismiss'), icon: 'cancel', onclick: dismissMode1 }"
        >
          Body text to provide context.
        </CmkAlert>
      </template>
    </section>

    <section>
      <h3>Mode 2: Without buttons, dismissible</h3>
      <p>Optional close icon. Dismissed on page reload.</p>
      <CmkAlert
        v-for="v in ['info', 'success'] as const"
        :key="v"
        :variant="v"
        heading="Headline"
        :dismissible="true"
      >
        Body text to provide context.
      </CmkAlert>
    </section>

    <section>
      <h3>Mode 2b: Without buttons, not dismissible</h3>
      <p>No close icon. Alert stays visible until the surrounding context changes.</p>
      <CmkAlert
        v-for="v in ['warning', 'error', 'loading'] as const"
        :key="v"
        :variant="v"
        heading="Headline"
      >
        Body text to provide context.
      </CmkAlert>
    </section>

    <section>
      <h3>Mode 3: Auto-dismiss (success only)</h3>
      <p>
        Dismissed automatically after 6 seconds.
        <button type="button" @click="reset">Reset</button>
      </p>
      <CmkAlert
        v-model:open="autoDismissOpen"
        variant="success"
        heading="Operation completed"
        :auto-dismiss="true"
      >
        This alert will dismiss automatically after 6 seconds.
      </CmkAlert>
    </section>

    <section>
      <h3>Sizes</h3>
      <CmkAlert variant="info" heading="Medium (default)">This is the medium size.</CmkAlert>
      <CmkAlert variant="info" size="small">This is the small size.</CmkAlert>
    </section>

    <section>
      <h3>Responsive behavior</h3>
      <p>Global — full container width</p>
      <CmkAlert variant="info" heading="This is a headline">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut
        labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco
        laboris nisi ut aliquip ex ea commodo consequat.
      </CmkAlert>
      <p>Contextual — narrow placement (~280px)</p>
      <div class="ucl-cmk-alert-dev__contextual">
        <CmkAlert
          variant="info"
          heading="This is a very long headline to test the responsive behavior of the alert box in a narrow container"
        >
          Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt
          ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation
          ullamco laboris nisi ut aliquip ex ea commodo consequat.
        </CmkAlert>
      </div>
    </section>
  </div>
</template>

<style scoped>
.ucl-cmk-alert-dev__contextual {
  max-width: 280px;
}
</style>
