<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from '@/components/CmkButton.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

const props = defineProps<{
  title: string
  subtitle?: string
  buttonText: string
  buttonUrl: string
}>()

const handleButtonClick = () => {
  window.open(props.buttonUrl, '_blank', 'noopener,noreferrer')
}
</script>

<template>
  <div class="ucl-footer">
    <div class="ucl-footer__content">
      <CmkHeading type="h2">{{ title }}</CmkHeading>
      <p class="ucl-footer__subtitle">{{ subtitle }}</p>
      <CmkButton variant="primary" @click="handleButtonClick">
        {{ buttonText }}
      </CmkButton>
    </div>
  </div>
</template>

<style scoped>
.ucl-footer {
  background-repeat: no-repeat;
  background-color: var(--ucl-elements-background-color);
  border-radius: 4px;
  padding: 40px 40px 40px 200px;
  display: flex;
  align-items: center;
  background-image:
    url('../assets/images/hexagon.svg'), url('../assets/images/hexagon.svg'),
    url('../assets/images/hexagon.svg');
  background-size: 100px;
  background-position:
    23px -50px,
    -30px 40px,
    right 0 bottom -40px;
}

@media (width < 1024px) {
  .ucl-footer {
    padding-top: 66px;
    padding-left: 80px;
  }
}

.ucl-footer__content {
  position: relative;
  max-width: 700px;
}

.ucl-footer__subtitle {
  line-height: 20px;
  margin: 0 0 24px;
}
</style>
