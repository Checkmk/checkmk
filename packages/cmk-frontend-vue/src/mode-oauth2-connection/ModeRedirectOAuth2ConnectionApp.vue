<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, onMounted } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkCopy from '@/components/CmkCopy.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import { OAUTH2_REDIRECT_MESSAGE_TYPE } from '@/mode-oauth2-connection/lib/waitForRedirect'

const { _t } = usei18n()

const queryParams = new URL(window.location.href).searchParams

const getCode = computed(() => {
  return queryParams.get('code')
})

const successfullyLoggedIn = computed(() => {
  return !!getCode.value
})

const showCopy = computed(() => {
  return queryParams.get('showcopy') === '1'
})

onMounted(() => {
  // targetOrigin matches the opener's origin since the redirect URL is same-site
  window.opener?.postMessage(
    { type: OAUTH2_REDIRECT_MESSAGE_TYPE, href: window.location.href },
    window.location.origin
  )
})

const title = computed(() => {
  if (successfullyLoggedIn.value) {
    return _t('Your login was successful!')
  }

  return _t('Your login was not successful. Please try again.')
})
</script>

<template>
  <Teleport to="body">
    <div class="mode-oauth2-connection-mode-redirect-o-auth2connection-app">
      <div class="mode-oauth2-connection-mode-redirect-o-auth2connection-app__content">
        <img src="themes/facelift/images/checkmk_logo.svg" width="150" />

        <CmkIcon v-if="successfullyLoggedIn" name="checkmark" size="xxxlarge" />
        <CmkMultitoneIcon v-else name="error" primary-color="danger" size="xxxlarge" />
        <div>
          <CmkHeading type="h1">{{ title }}</CmkHeading>
          <CmkHeading v-if="showCopy && successfullyLoggedIn" type="h3">
            {{ _t('Please copy the code, then you can close this tab.') }}
          </CmkHeading>
          <CmkHeading v-else type="h3">{{ _t('You can now close this tab.') }}</CmkHeading>
        </div>
        <template v-if="successfullyLoggedIn && showCopy">
          <CmkCopy :text="getCode || ''">
            <CmkButton>
              <CmkIcon name="copied" variant="inline" size="medium" />
              {{ _t('Copy code to clipboard') }}
            </CmkButton>
          </CmkCopy>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.mode-oauth2-connection-mode-redirect-o-auth2connection-app {
  position: fixed;
  inset: 0;
  background: var(--default-bg-color);
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 4000;

  .mode-oauth2-connection-mode-redirect-o-auth2connection-app__content {
    background: var(--ux-theme-0);
    width: 500px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--dimension-10);
    padding: var(--dimension-10);

    div {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--dimension-10);
    }
  }
}
</style>
