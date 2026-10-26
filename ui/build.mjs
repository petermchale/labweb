import {build} from 'esbuild';
import {writeFileSync} from 'node:fs';
const result=await build({entryPoints:['ui/src/main.js'],bundle:true,outfile:'viewer.js',write:false,format:'iife',target:'es2022',minify:true,legalComments:'inline'});
const js=result.outputFiles.find(f=>f.path.endsWith('.js')).text.replaceAll('</script','<\\/script');
const css=result.outputFiles.find(f=>f.path.endsWith('.css')).text;
writeFileSync('labkg/app.html',`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Labweb evidence</title><style>${css}</style></head><body><p id="status" aria-live="polite">Waiting for graph data…</p><main id="labweb"></main><script type="application/json" id="labkg-data">__DATA__</script><script>${js}</script></body></html>`);

await build({entryPoints:['ui/src/a2ui.js'],bundle:true,outfile:'ui/.build/a2ui.js',format:'esm',target:'es2022'});
