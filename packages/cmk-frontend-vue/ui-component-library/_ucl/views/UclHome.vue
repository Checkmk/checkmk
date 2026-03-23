<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSpace from '@/components/CmkSpace.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import demoLayoutImage from '../assets/images/ucl-layout.png'
import UclHeroBanner from '../components/UclHeroBanner.vue'
import HomeLayout from '../components/UclHomeLayout.vue'
import UclInfoCard from '../components/UclInfoCard.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <HomeLayout>
    <template #header>
      <UclHeroBanner title="Checkmk UI Component Library" subtitle="UI components behind Checkmk" />
    </template>

    <template #intro>
      <CmkHeading type="h1">The single source of truth for Checkmk UI components</CmkHeading>
      <p>
        Explore, understand, and use Vue UI components consistently across Checkmk — with real
        behavior, real code, and no guesswork.
      </p>

      <div>
        <p><strong>A centralized reference to:</strong></p>
        <ul>
          <li>Discover which UI components exist</li>
          <li>See how components look and behave in reality</li>
          <li>Understand supported variants and states</li>
          <li>Access example usage and source code snippets</li>
          <li>Reduce ambiguity and rework across teams</li>
        </ul>
      </div>
    </template>

    <template #feature-left>
      <CmkHeading type="h1">What’s included</CmkHeading>
      <CmkSpace size="medium" direction="vertical" />
      <CmkHeading type="h2">Components</CmkHeading>
      <p>
        Components are reusable, functional UI building blocks built on top of the foundations that
        meet specific interaction needs. They are designed to be consistent, accessible, and
        scalable, and are implemented in Vue for use across different use cases and projects.
      </p>
    </template>

    <template #feature-right>
      <img
        :src="demoLayoutImage"
        alt="Component screenshot"
        style="max-width: 100%; max-height: 100%; object-fit: contain"
      />
    </template>

    <template #audience-title>
      <CmkHeading type="h1">Audience and usage</CmkHeading>
    </template>

    <template #audience-cards>
      <UclInfoCard
        icon-name="development"
        title="Development"
        variant="borderless"
        :bullet-points="[
          'Use as the first stop before building UI',
          'Search for existing components instead of re-implementing',
          'Review real behavior, variants, and states',
          'Use the detailed page as a reference during implementation and reviews',
          'Base new component usage on the provided structure and examples'
        ]"
      />
      <UclInfoCard
        icon-name="ux"
        title="UX"
        variant="borderless"
        :bullet-points="[
          'Use to verify design consistency against what is actually implemented',
          'Validate that components behave as expected across states',
          'Use it as a shared reference when discussing design decisions with developers',
          'Identify potential design gaps or inconsistencies before development'
        ]"
      />
      <UclInfoCard
        icon-name="product"
        title="Product"
        variant="borderless"
        :bullet-points="[
          'Use as a shared reference during feature discussions',
          'Validate what UI components already exist before proposing new ones',
          'Align expectations with Development and UX using a common, concrete baseline',
          'Reduce ambiguity in requirements by referencing existing components and behavior'
        ]"
      />
      <UclInfoCard
        icon-name="qa"
        title="QA"
        variant="borderless"
        :bullet-points="[
          'Use as a baseline for expected behavior',
          'Validate UI behavior and states against what is documented in the component pages',
          'Identify inconsistencies between implemented features and component definitions',
          'Use it to support regression testing and exploratory testing scenarios'
        ]"
      />
    </template>
  </HomeLayout>
</template>
