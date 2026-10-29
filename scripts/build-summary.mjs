import { readFileSync, writeFileSync } from "node:fs";
const { _ } = JSON.parse(readFileSync("data/bundled-data.json","utf8"));
writeFileSync("data/catalogue-summary.json",JSON.stringify({medicine_count:_.c.m,pharmacy_count:_.c.p,atc_count:_.c.a,valid_from:_.sources?.medicines?.valid_from ?? null,valid_until:_.sources?.medicines?.valid_until ?? null},null,2)+"\n");
