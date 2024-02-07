# frontend_vue

Checkmk vue experiments

## known problems

nodejs/npm is okay with not self contained projects. this means, all parent
folders having node_modules folders are considered valid dependencies. we ignore
this for now in this package. it will be resolved when we move all javascript
code into the packages subfolder.

## development

```sh
npm install
npm run dev
npm run build
npm run lint
npm run format
```
