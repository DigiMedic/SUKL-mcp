import { it, expect } from "vitest";
import { App } from "@modelcontextprotocol/ext-apps";
import { AppBridge } from "@modelcontextprotocol/ext-apps/app-bridge";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";

it("completes MCP Apps tool calls and external navigation, including a recoverable upstream failure", async () => {
  const app = new App({name:"medicine-widget",version:"1.0.1"},{},{autoResize:false});
  const bridge = new AppBridge(null,{name:"validation-host",version:"1"},{serverTools:{},openLinks:{}});
  const [view,host] = InMemoryTransport.createLinkedPair();
  const calls:unknown[] = []; const links:string[] = [];
  bridge.oncalltool = async params => {
    calls.push(params);
    return calls.length === 1 ? {content:[],structuredContent:{status:"ok",document:{url:"https://prehledy.sukl.cz/dlp/v1/dokumenty/123",content_included:false}}} : {isError:true,content:[{type:"text",text:"Synthetic upstream outage"}]};
  };
  bridge.onopenlink = async ({url}) => {links.push(url);return {};};
  try {
    await bridge.connect(host); await app.connect(view);
    const request = {name:"get_medicine_document",arguments:{sukl_code:"0254045",document_type:"PIL"}};
    const result = await app.callServerTool(request);
    expect(result.structuredContent).toMatchObject({document:{content_included:false}});
    expect(await app.openLink({url:"https://prehledy.sukl.cz/dlp/v1/dokumenty/123"})).not.toMatchObject({isError:true});
    expect(calls[0]).toMatchObject(request); expect(links).toEqual(["https://prehledy.sukl.cz/dlp/v1/dokumenty/123"]);
    expect((await app.callServerTool(request)).isError).toBe(true);
  } finally {await app.close();await bridge.close();}
});
