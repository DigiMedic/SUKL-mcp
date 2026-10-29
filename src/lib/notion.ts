/**
 * Notion API client for form submissions (CRM)
 * Sends leads, enterprise contacts, and newsletter signups to Notion databases
 */

import { Client } from "@notionhq/client";

const notion = new Client({
  auth: process.env.NOTION_API_KEY,
  timeoutMs: 10000,
  retry: { maxRetries: 1, maxRetryDelayMs: 1000 },
});

const DB_LEADS = process.env.NOTION_DB_LEADS ?? "";
const DB_ENTERPRISE = process.env.NOTION_DB_ENTERPRISE ?? "";
const DB_NEWSLETTER = process.env.NOTION_DB_NEWSLETTER ?? "";

export async function createLead(data: {
  email: string;
  company: string;
  useCase: string;
  name: string;
  useCaseDetail?: string;
  gdprConsentAt: string;
}) {
  return notion.pages.create({
    parent: { database_id: DB_LEADS },
    properties: {
      Email: { email: data.email },
      Firma: { title: [{ text: { content: data.company } }] },
      "Use Case": { select: { name: data.useCase } },
      Jméno: { rich_text: [{ text: { content: data.name } }] },
      ...(data.useCaseDetail
        ? { "Use Case Detail": { rich_text: [{ text: { content: data.useCaseDetail } }] } }
        : {}),
      "GDPR Souhlas": { date: { start: data.gdprConsentAt } },
      Datum: { date: { start: new Date().toISOString().split("T")[0] } },
      Status: { select: { name: "Nový" } },
    },
  });
}

export async function createEnterpriseContact(data: {
  email: string;
  company: string;
  phone?: string;
  companySize: string;
  message: string;
  name: string;
  gdprConsentAt: string;
}) {
  return notion.pages.create({
    parent: { database_id: DB_ENTERPRISE },
    properties: {
      Email: { email: data.email },
      Firma: { title: [{ text: { content: data.company } }] },
      Jméno: { rich_text: [{ text: { content: data.name } }] },
      Telefon: { phone_number: data.phone || null },
      Velikost: { select: { name: data.companySize } },
      Zpráva: { rich_text: [{ text: { content: data.message } }] },
      "GDPR Souhlas": { date: { start: data.gdprConsentAt } },
      Datum: { date: { start: new Date().toISOString().split("T")[0] } },
    },
  });
}

export async function checkNewsletterDuplicate(email: string): Promise<boolean> {
  const database = await notion.databases.retrieve({ database_id: DB_NEWSLETTER });
  if (!("data_sources" in database) || database.data_sources.length !== 1) throw new Error("Newsletter requires exactly one configured Notion data source.");
  const result = await notion.dataSources.query({ data_source_id: database.data_sources[0].id, filter: { property: "Email", email: { equals: email.toLowerCase() } }, page_size: 1 });
  return result.results.length > 0;
}

export async function createNewsletterSubscriber(email: string, gdprConsentAt: string) {
  return notion.pages.create({
    parent: { database_id: DB_NEWSLETTER },
    properties: {
      Name: { title: [{ text: { content: email.toLowerCase() } }] },
      Email: { email: email.toLowerCase() },
      "GDPR Souhlas": { date: { start: gdprConsentAt } },
      Datum: { date: { start: new Date().toISOString().split("T")[0] } },
    },
  });
}
