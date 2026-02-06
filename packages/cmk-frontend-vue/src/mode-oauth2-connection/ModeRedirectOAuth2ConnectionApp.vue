<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

const { _t } = usei18n()

const successfullyLoggedIn = computed(() => {
  const params = new URL(window.location.href).searchParams
  return !!params.get('code')
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
          <CmkHeading type="h3">{{ _t('You can now close this tab.') }}</CmkHeading>
        </div>
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
