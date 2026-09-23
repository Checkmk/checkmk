/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import MonitoringSurveyLink from '@/monitoring/shared/components/MonitoringSurveyLink.vue'

const SURVEY_URL = 'https://survey.example/new-view'

test('points at the survey and opens it in a new tab', () => {
  render(MonitoringSurveyLink, { props: { url: SURVEY_URL } })

  const link = screen.getByRole('link', { name: /Give feedback/ })

  expect(link).toHaveAttribute('href', SURVEY_URL)
  expect(link).toHaveAttribute('target', '_blank')
})
