import { build } from "esbuild";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
mkdirSync("widgets/dist", { recursive: true });
for (const preview of [false, true]) {
  const result = await build({ entryPoints:["widgets/medicines.ts"], bundle:true, write:false, format:"esm", target:"es2022", minify:true, define:{ __PREVIEW__:String(preview) } });
  const script = result.outputFiles[0].text.replace(/<\/script/gi,"<\\/script");
  const html = readFileSync("widgets/medicines.html", "utf8").replace("/*__APP_SCRIPT__*/", () => script);
  writeFileSync(`widgets/dist/${preview ? "preview" : "medicines"}.html`, html);
}
