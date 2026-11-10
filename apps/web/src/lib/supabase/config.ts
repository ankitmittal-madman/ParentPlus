import { isFounderTestBackend } from "../founder/backend-boundary";
/**
 * Public Supabase configuration.
 * Never use a service-role key in browser code.
 */
export function getSupabaseConfig() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey =
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

  if (!url || !publishableKey) {
    throw new Error(
      "Missing public Supabase environment configuration"
    );
  }

  const parsed = new URL(url);

  const loopback = ["localhost", "127.0.0.1", "[::1]"].includes(parsed.hostname);
  if (parsed.username || parsed.password ||
      (parsed.protocol !== "https:" && !(parsed.protocol === "http:" && loopback))) {
    throw new Error("Invalid Supabase URL protocol");
  }

  if (process.env.NEXT_PUBLIC_FOUNDER_MODE === "true" && url !== "http://127.0.0.1:54321" && !isFounderTestBackend(url, process.env.NEXT_PUBLIC_FOUNDER_TEST_PROJECT_REF)) {
    throw new Error("Founder testing requires the selected test backend");
  }
  return { url, publishableKey };
}
