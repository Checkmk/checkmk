<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

const { t } = usei18n('welcome-app')
</script>

<template>
  <h1>{{ t('header', 'Welcome to Checkmk!') }}</h1>
  <!-- eslint-disable vue/no-bare-strings-in-template -->
  <p>
    This is just a placeholder for the Welcome page. It will be used to guide you through the first
    steps of using Checkmk.
  </p>
  <p>
    In case you want to change the start URL to the main dashboard, you can do so under User/Edit
    profile/Start URL.
  </p>
  <!-- eslint-enable vue/no-bare-strings-in-template -->
</template>

<style scoped></style>
