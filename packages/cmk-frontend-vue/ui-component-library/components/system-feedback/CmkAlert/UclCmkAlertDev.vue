<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
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

const variants = ['info', 'success', 'warning', 'error', 'loading'] as const

// This demo key is deliberately not one of the warnings the server knows, so
// the dismissal it sends is a no-op the backend rejects. A real key would
// dismiss that warning in the user config of whoever opens the library.
// @ts-expect-error demo-only key, not a DismissableWarning
const { isShown: mode1Shown, dismiss: dismissMode1 } = useDismissDialog('ucl_cmk_alert_demo')
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
      <h3>Small: single line next to the issue</h3>
      <p>No heading, no buttons. The width follows the text.</p>
      <div class="ucl-cmk-alert-dev__stack">
        <CmkAlert
          v-for="v in variants"
          :key="v"
          :variant="v"
          size="small"
          :text="_t('Body text to provide context')"
        />
      </div>
    </section>

    <section>
      <h3>Small: dismissible (info and success only)</h3>
      <div class="ucl-cmk-alert-dev__stack">
        <CmkAlert
          v-for="v in ['info', 'success'] as const"
          :key="v"
          :variant="v"
          size="small"
          :dismissible="true"
          :text="_t('Body text to provide context')"
        />
      </div>
    </section>

    <section>
      <h3>Small: long text is cut off, hover shows it all</h3>
      <div class="ucl-cmk-alert-dev__contextual">
        <CmkAlert
          variant="info"
          size="small"
          :text="
            _t(
              'The assertion consumer service endpoint is derived from the site URL and cannot be changed here.'
            )
          "
        />
      </div>
    </section>

    <section>
      <h3>Medium: with buttons</h3>
      <p>
        Heading and text required. No close icon. Dismissed via buttons only.
        <button v-if="!mode1Shown" type="button" @click="resetMode1">Reset</button>
      </p>
      <template v-if="mode1Shown">
        <CmkAlert
          v-for="v in ['info', 'success', 'warning', 'error'] as const"
          :key="v"
          :variant="v"
          :heading="_t('Headline')"
          :text="_t('Body text to provide context.')"
          :main-button="{ title: _t('Confirm'), onclick: () => {} }"
          :optional-button="{ title: _t('Dismiss'), icon: 'cancel', onclick: dismissMode1 }"
        />
      </template>
    </section>

    <section>
      <h3>Medium: dismissible (info and success only)</h3>
      <CmkAlert
        v-for="v in ['info', 'success'] as const"
        :key="v"
        :variant="v"
        :heading="_t('Headline')"
        :text="_t('Body text to provide context.')"
        :dismissible="true"
      />
    </section>

    <section>
      <h3>Medium: not dismissible</h3>
      <CmkAlert
        v-for="v in ['warning', 'error', 'loading'] as const"
        :key="v"
        :variant="v"
        :heading="_t('Headline')"
        :text="_t('Body text to provide context.')"
      />
    </section>

    <section>
      <h3>Medium: auto-dismiss (success only)</h3>
      <p>
        Dismissed automatically after 6 seconds.
        <button type="button" @click="reset">Reset</button>
      </p>
      <CmkAlert
        v-model:open="autoDismissOpen"
        variant="success"
        :heading="_t('Operation completed')"
        :text="_t('This alert will dismiss automatically after 6 seconds.')"
        :auto-dismiss="true"
      />
    </section>

    <section>
      <h3>Medium: narrow placement (~280px)</h3>
      <div class="ucl-cmk-alert-dev__contextual">
        <CmkAlert
          variant="info"
          :heading="
            _t(
              'This is a very long headline to test the responsive behavior of the alert box in a narrow container'
            )
          "
          :text="
            _t(
              'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
            )
          "
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.ucl-cmk-alert-dev__stack {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--dimension-3);
}

.ucl-cmk-alert-dev__contextual {
  max-width: 280px;
}
</style>
