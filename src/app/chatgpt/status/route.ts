import { getCatalogueProvenance } from "@/lib/sukl-client";
import { sharedRateLimitConfigured } from "@/lib/shared-rate-limit";
export const dynamic = "force-dynamic";
export async function GET() {
  const provenance = getCatalogueProvenance();
  const readiness = { current_catalogue:provenance.freshness === "current", policy_confirmed:process.env.PUBLICATION_POLICY_CONFIRMED === "true" && Boolean(process.env.PRIVACY_HOST_LOG_RETENTION && process.env.PRIVACY_FORM_RETENTION && process.env.PRIVACY_REDIS_PROVIDER), shared_limits_configured:sharedRateLimitConfigured(), public_launch_mode:process.env.PUBLIC_LAUNCH_MODE === "true", analytics_disabled:process.env.NEXT_PUBLIC_ENABLE_ANALYTICS !== "true" };
  return Response.json({ ready_for_host_testing:Object.values(readiness).every(Boolean), readiness, provenance }, { headers:{"Cache-Control":"no-store"} });
}
