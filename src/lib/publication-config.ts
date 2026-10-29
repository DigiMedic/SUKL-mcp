export function legacyFormsEnabled() {
  return process.env.NODE_ENV !== "production" || process.env.LEGACY_FORMS_ENABLED === "true";
}

export function publicationPoliciesReady() {
  return process.env.PUBLICATION_POLICY_CONFIRMED === "true"
    && Boolean(process.env.PRIVACY_HOST_LOG_RETENTION?.trim())
    && Boolean(process.env.PRIVACY_REDIS_PROVIDER?.trim())
    && (!legacyFormsEnabled() || Boolean(process.env.PRIVACY_FORM_RETENTION?.trim()));
}
