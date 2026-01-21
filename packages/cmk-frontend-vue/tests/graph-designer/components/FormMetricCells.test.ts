/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'

import FormMetricCells from '@/graph-designer/private/FormMetricCells.vue'

test('Render FormMetricCells', () => {
  render(FormMetricCells)
})
