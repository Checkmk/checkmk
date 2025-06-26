<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'
import usei18n from '@/lib/i18n'
import CmkCheckbox from '@/components/CmkCheckbox.vue'
import CmkBodyText from '@/components/typography/CmkBodyText.vue'

const { t } = usei18n('welcome-footer')

const showWelcomeOnStart = ref(true)
</script>

<template>
  <section class="welcome-footer">
    <CmkCheckbox
      v-model="showWelcomeOnStart"
      :label="t('show-on-start', 'Show welcome page on start (not implemented yet)')"
    />
    <CmkBodyText class="welcome-footer__hint">
      {{
        t(
          'access-breadcrumbs',
          'You can still access it later via Help > Learning Checkmk > Get started'
        )
      }}
    </CmkBodyText>
  </section>
</template>

<style scoped>
.welcome-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
}

.welcome-footer__hint {
  color: var(--font-color-dimmed);
  margin-top: 4px;
}
</style>
