# cmk-frontend-vue

Checkmk vue experiments

## known problems

nodejs/npm is okay with not self contained projects. this means, all parent
folders having node_modules folders are considered valid dependencies. we ignore
this for now in this package. it will be resolved when we move all javascript
code into the packages subfolder.

## development

```sh
npm install
npm run build
npm run lint
npm run format
```

### trying out changes in a site

#### f12

f12 is working, but is using the production ready build process and therefore not
super fast (currently six seconds)

#### vite dev server

To combine both the vite auto hot reload and the site, the proxy feature of the
vite dev server is used.

* run `npm run dev`
* surf to `http://localhost:5173/<yoursite>/checkmk/` (tailing slash is
  important, otherwise checkmk will redirect to a url without the port)
* enable "Inject cmk-frontend-vue files via vite client" in "User Interface"
  in "Experimental Features" in "global settings"

Checkmk should then automatically reload as soon as you change a file of the
cmk-frontend-vue project.
