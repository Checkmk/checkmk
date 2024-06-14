import type { App } from 'vue'

export function mixinUniqueId(app: App<Element>) {
  let uniqueId = 0
  app.mixin({
    beforeCreate: function () {
      this.$componentId = `comp_${uniqueId}`
      uniqueId += 1
    }
  })
}
