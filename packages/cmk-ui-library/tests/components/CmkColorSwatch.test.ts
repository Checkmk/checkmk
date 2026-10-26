/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import CmkColorSwatch from 'cmk-ui-library/components/CmkColorSwatch.vue'

test('shows the given color', () => {
  const { container } = render(CmkColorSwatch, { props: { color: '#3cc2ff' } })

  expect(container.querySelector('.cmk-color-swatch')).toHaveStyle({
    backgroundColor: 'rgb(60, 194, 255)'
  })
})
