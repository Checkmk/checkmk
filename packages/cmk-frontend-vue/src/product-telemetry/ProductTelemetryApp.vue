<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type ProductTelemetryConfig } from 'cmk-shared-typing/typescript/product_telemetry'
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkPopupDialog from '@/components/CmkPopupDialog.vue'
import CmkSpace from '@/components/CmkSpace.vue'

const { _t } = usei18n()

const props = defineProps<ProductTelemetryConfig>()

const popupOpen = ref(true)
</script>

<template>
  <CmkPopupDialog
    :open="popupOpen"
    :title="_t('Help us improve Checkmk with product telemetry')"
    :stay-open-overlay-click="true"
    @close="popupOpen = false"
  >
    <div class="product-telemetry-app__content">
      <h4>{{ _t('Why do we need product telemetry in Checkmk?') }}</h4>

      <p>
        {{
          _t(
            'Help us shape the future of Checkmk. Your usage data allows us to make better decisions and focus development on the tools you use regularly. Please consider consenting to Product Telemetry to help us build the features that matter the most to you.'
          )
        }}
      </p>
      <CmkSpace direction="horizontal" />
      <h4>{{ _t('What data are we collecting?') }}</h4>
      <p>{{ _t('We strictly limit data collection to aggregated, non-personal metrics.') }}</p>
      <ul>
        <li>
          <b>{{ _t('We Collect:') }}</b
          >{{ _t('Quantity metrics (e.g., count of hosts, folders, and services).') }}
        </li>
        <li>
          <b>{{ _t('We Do NOT Collect:') }}</b
          >{{
            _t(
              'User behavior (e.g., visit frequency) or sensitive identifiers (e.g., hostnames, file paths, service names, or raw metric values).'
            )
          }}
        </li>
      </ul>
      <CmkSpace direction="horizontal" />
      <h4>{{ _t('Do we automatically collect and send data?') }}</h4>
      <p>
        {{
          _t(
            'No! We firmly believe in only receiving data you are happy to share with us. For this reason, on default product telemetry is turned off. To make a decision now, please click on the "Decide on product telemetry" button.'
          )
        }}
      </p>
    </div>

    <div class="product-telemetry-app__buttons">
      <CmkButton variant="secondary" @click="popupOpen = false">{{ _t('Ask me again') }}</CmkButton>
      <a
        class="product-telemetry-app__link"
        :href="props.global_settings_link"
        target="main"
        @click="popupOpen = false"
        >{{ _t('Enable in global settings') }}</a
      >
    </div>
  </CmkPopupDialog>
</template>

<style scoped>
.product-telemetry-app__content {
  padding: var(--dimension-4) var(--dimension-4) var(--dimension-10) var(--dimension-4);
}

.product-telemetry-app__buttons {
  display: flex;
  justify-content: flex-end;
  gap: var(--dimension-8);
}

.product-telemetry-app__link {
  color: var(--button-primary-text-color);
  background-color: var(--default-button-primary-color);
  border: var(--dimension-1) solid var(--button-primary-border-color);
  padding: 0 var(--dimension-4);
  text-decoration: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--dimension-3);

  &:hover {
    background-color: color-mix(in srgb, var(--default-button-primary-color) 70%, var(--white) 30%);
  }

  &:active {
    background-color: color-mix(
      in srgb,
      var(--default-button-primary-color) 90%,
      var(--color-conference-grey-10) 10%
    );
  }
}
</style>
