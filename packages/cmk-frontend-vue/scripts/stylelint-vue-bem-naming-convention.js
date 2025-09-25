/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
//
// stylelint plugin to check if all classes inside vue components adhere to bem naming standard
//
// echo '.foo {}' | stylelint --stdin-filename=test.css
// echo '<style>.foo {}</style>' | ./node_modules/.bin/stylelint --stdin-filename=LongCamelCaseComponentName.vue
import * as path from 'path'
import stylelint from 'stylelint'
import getRuleSelector from 'stylelint/lib/utils/getRuleSelector.mjs'
import parseSelector from 'stylelint/lib/utils/parseSelector.mjs'

const {
  createPlugin,
  utils: { report, ruleMessages, validateOptions }
} = stylelint

const ruleName = 'checkmk/vue-bem-naming-convention'

const messages = ruleMessages(ruleName, {
  start: (selector, selectorPrefix) =>
    `Class selector "${selector}" should start with block name "${selectorPrefix}"`,
  first: (blockName) =>
    `Block name "${blockName}" should be followed by either "--" for modifiers or "__" for elements`,
  modifier: (modifier) =>
    `Modifier should only contain lower case alphanumerical characters and single dashes, got "${modifier}"`,
  element: (element) =>
    `Element should only contain lower case alphanumerical characters and single dashes or one double dash, got "${element}"`
})

const meta = {}

function convertCamelToKebabCase(str) {
  return str.replace(/([a-zA-Z])(?=[A-Z])/g, '$1-').toLowerCase()
}

function shortPrefix(str, longName, shortName) {
  if (longName === 'dashboard-wip') {
    longName = 'dashboard'
  }
  if (str.startsWith(longName)) {
    return str.replace(new RegExp(`^${longName}`), shortName)
  }
  return str
}

const projectRoot = path.join(import.meta.dirname, '../')

const patternMap = {
  // make sure the thing we map to is unique:
  demo: 'demo/',
  '': 'src/assets/',
  cmk: 'src/components/',
  db: 'src/dashboard-wip/',
  qs: 'src/quick-setup/',
  gd: 'src/graph-designer/',
  mm: 'src/main-menu/',
  mh: 'src/mode-host/'
}

function getPrefix(relativePath) {
  const folderName = relativePath.split('/')[1]
  for (let [key, value] of Object.entries(patternMap)) {
    if (relativePath.startsWith(value)) {
      return [folderName, key]
    }
  }
  return [folderName, folderName]
}

/** @type {import('stylelint').Rule} */
const ruleFunction = (primary, secondaryOptions, context) => {
  return (root, result) => {
    const validOptions = validateOptions(result, ruleName, {
      actual: primary,
      possible: [true]
    })

    if (!validOptions) return

    root.walkRules((ruleNode) => {
      const relativeFilePath = path.relative(projectRoot, ruleNode.source.input.file)

      const [componentNane, prefix] = getPrefix(relativeFilePath)

      const filePathParsed = path.parse(ruleNode.source.input.file)
      if (filePathParsed.ext !== '.vue') {
        return
      }

      let selectorName = shortPrefix(
        convertCamelToKebabCase(filePathParsed.name),
        componentNane,
        prefix
      )
      if (!selectorName.startsWith(prefix)) {
        selectorName = `${prefix}-${selectorName}`
      }
      const expectedSelector = `.${selectorName}`

      const selectorRoot = parseSelector(getRuleSelector(ruleNode), result, ruleNode)
      if (!selectorRoot) {
        return
      }
      selectorRoot.walkClasses((classNode) => {
        const selector = String(classNode).trim()
        if (selector == expectedSelector) {
          return
        }
        if (!selector.startsWith(expectedSelector)) {
          report({
            result,
            ruleName,
            message: messages.start(selector, expectedSelector),
            node: ruleNode,
            word: selector
          })
          return
        }
        const elementOrModifier = selector.substring(expectedSelector.length)
        if (elementOrModifier.startsWith('--')) {
          const modifier = elementOrModifier.substring(2)
          if (!modifier.match('^[a-z]([a-z0-9]-?)*$')) {
            report({
              result,
              ruleName,
              message: messages.modifier(modifier),
              node: ruleNode,
              word: selector
            })
            return
          }
        } else if (elementOrModifier.startsWith('__')) {
          const element = elementOrModifier.substring(2)
          if (!element.match('^[a-z]([a-z0-9]-?-?)*$') || (element.match(/--/g) || []).length > 1) {
            report({
              result,
              ruleName,
              message: messages.element(element),
              node: ruleNode,
              word: selector
            })
            return
          }
        } else {
          report({
            result,
            ruleName,
            message: messages.first(expectedSelector),
            node: ruleNode,
            word: selector
          })
          return
        }
      })
    })
  }
}

ruleFunction.ruleName = ruleName
ruleFunction.messages = messages
ruleFunction.meta = meta

export default createPlugin(ruleName, ruleFunction)
