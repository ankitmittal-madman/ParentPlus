/** Server-only configuration; never import this module from a client component. */
import { getSupabaseConfig } from "../supabase/config";
import { isFounderTestBackend } from "./backend-boundary";
export function founderConfig() {
  if (process.env.PARENTPLUS_FOUNDER_MODE !== "true" || process.env.NEXT_PUBLIC_FOUNDER_MODE !== "true") return null;
  try {
    const { url, publishableKey } = getSupabaseConfig();
    if (process.env.NODE_ENV === "development" && url === "http://127.0.0.1:54321") {
      const serviceKey = process.env.PARENTPLUS_LOCAL_SERVICE_KEY;
      return serviceKey ? { url, publishableKey, serviceKey, mode: "local" as const, projectRef: null } : null;
    }
    const projectRef = process.env.NEXT_PUBLIC_FOUNDER_TEST_PROJECT_REF;
    if (process.env.PARENTPLUS_APP_STAGE !== "testing" || !isFounderTestBackend(url, projectRef)) return null;
    const serviceKey = process.env.PARENTPLUS_TEST_SERVICE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;
    return serviceKey ? { url, publishableKey, serviceKey, mode: "hosted-testing" as const, projectRef: projectRef! } : null;
  } catch { return null; }
}
