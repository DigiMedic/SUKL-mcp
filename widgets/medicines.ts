import { App, applyHostStyleVariables } from "@modelcontextprotocol/ext-apps";
import type { catalogueMedicine } from "../src/lib/chatgpt-catalogue";
type Medicine = ReturnType<typeof catalogueMedicine>;
interface Payload { medicines?: Medicine[]; missing_codes?: string[]; provenance?: { bundle_created_at: string; source_as_of: string | null; source_valid_until?: string | null; warning: string } }

const app = new App({ name: "sukl-catalogue", version: "1.0.1" }, {});
const cards = document.getElementById("cards")!;
const status = document.getElementById("status")!;
const provenance = document.getElementById("provenance")!;
document.getElementById("data-terms")!.onclick = async event => {
  if (__PREVIEW__) return;
  event.preventDefault();
  try { const result = await app.openLink({ url: "https://opendata.sukl.gov.cz/?q=podminky-uziti-otevrenych-dat" }); if (result.isError) status.textContent = "Podmínky dat se nepodařilo otevřít."; }
  catch { status.textContent = "Podmínky dat se nepodařilo otevřít."; }
};
function element<K extends keyof HTMLElementTagNameMap>(tag: K, text: string) {
  const node = document.createElement(tag); node.textContent = text; return node;
}
function render(payload: Payload) {
  cards.replaceChildren();
  for (const med of payload.medicines ?? []) {
    const card = document.createElement("article");
    card.append(element("h2", med.name), element("p", `${med.strength ?? ""} · ${med.form ?? ""} · ${med.package ?? ""}`));
    const dl = document.createElement("dl");
    for (const [label, value] of [["SÚKL", med.sukl_code], ["ATC", med.atc_code ?? "Neuvedeno"], ["Látky", med.reported_substance ?? "Neuvedeno"]]) dl.append(element("dt", label), element("dd", value));
    card.append(dl);
    const actions = document.createElement("div"); actions.className = "actions";
    for (const [type, label] of [["PIL", "Příbalová informace"], ["SPC", "Údaje o přípravku"]]) {
      const button = element("button", label);
      button.setAttribute("aria-label", `${label}: ${med.name}, kód SÚKL ${med.sukl_code}`);
      button.onclick = async () => {
        button.disabled = true; status.textContent = "Vyhledávám dokument u SÚKL…";
        try {
          const result = await app.callServerTool({ name: "get_medicine_document", arguments: { sukl_code: med.sukl_code, document_type: type } });
          const data = result.structuredContent as { document?: { url: string } } | undefined;
          const url = data?.document?.url;
          if (!result.isError && url && /^https:\/\/prehledy\.sukl\.cz\/dlp\/v1\/dokumenty\/\d+$/.test(url)) {
            const opened = await app.openLink({ url });
            status.textContent = opened.isError ? "Dokument se nepodařilo otevřít." : "Dokument je otevřen na webu SÚKL.";
          } else status.textContent = result.isError ? "SÚKL nyní není dostupný. Zkuste to později." : "Tento dokument nebyl nalezen.";
        } catch { status.textContent = "Dokument se nepodařilo načíst. Zkuste to později."; }
        finally { button.disabled = false; }
      };
      actions.append(button);
    }
    card.append(actions); cards.append(card);
  }
  status.textContent = payload.missing_codes?.length ? `Nenalezené kódy: ${payload.missing_codes.join(", ")}` : `${payload.medicines?.length ?? 0} zobrazených přípravků`;
  provenance.textContent = payload.provenance ? `${payload.provenance.source_as_of ? `Platnost katalogu: ${payload.provenance.source_as_of}${payload.provenance.source_valid_until ? ` až ${payload.provenance.source_valid_until}` : ""}.` : `Snímek vytvořen ${payload.provenance.bundle_created_at.slice(0, 10)}.`} ${payload.provenance.warning}` : "Datum katalogu není k dispozici.";
}
app.ontoolresult = result => { if (result.isError) status.textContent = "Výsledky nyní nelze zobrazit. Zkuste požadavek později."; else if (result.structuredContent) render(result.structuredContent as Payload); };
app.onhostcontextchanged = context => { document.documentElement.classList.toggle("dark", context.theme === "dark"); if (context.styles?.variables) applyHostStyleVariables(context.styles.variables); };

// Local preview is enabled only in a separate development bundle, never in the MCP resource.
declare const __PREVIEW__: boolean;
if (__PREVIEW__) {
  const { medicines, provenance } = await fetch("/api/chatgpt/preview-data").then(r => r.json());
  render({ medicines, provenance });
  document.querySelectorAll("button").forEach(button => { button.disabled = true; });
} else {
  try {
    await app.connect();
    const context = app.getHostContext();
    document.documentElement.classList.toggle("dark", context?.theme === "dark");
    if (context?.styles?.variables) applyHostStyleVariables(context.styles.variables);
  } catch { status.textContent = "Připojení ke konverzaci se nepodařilo. Údaje použijte z textové odpovědi."; }
}
