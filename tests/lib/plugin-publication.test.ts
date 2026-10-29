import { it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { strFromU8, strToU8 } from "fflate";
import { validatePluginFiles } from "../../scripts/plugin-validation.mjs";
function fixture() {
  return Object.fromEntries(["plugin.json","mcp.json","assets/icon.svg","skills/get-started/SKILL.md"].map(name => [name,new Uint8Array(readFileSync(`plugins/sukl-medicines/${name}`))]));
}
it("accepts the catalogue package and rejects invalid review metadata, embedded credentials and inaccessible branding", () => {
  const files = fixture(); expect(validatePluginFiles(files).issues).toEqual([]);
  const manifest = JSON.parse(strFromU8(files["plugin.json"]));
  const openai = manifest.extensions["com.openai"];
  openai.review.test_cases.positive[0].prompt = 123;
  openai.review.test_credentials = "synthetic-forbidden-placeholder";
  openai.interface.brandColor = "#FFFFFF";
  openai.interface.supportURL = "https://user:password@example.com/support";
  files["plugin.json"] = strToU8(JSON.stringify(manifest));
  const {issues} = validatePluginFiles(files);
  expect(issues).toEqual(expect.arrayContaining([
    "Review: expected 5 complete positive cases.",
    "Review: private access information must stay outside the ZIP.",
    "Listing: insufficient brandColor contrast.",
    "Listing: invalid supportURL.",
  ]));
});
