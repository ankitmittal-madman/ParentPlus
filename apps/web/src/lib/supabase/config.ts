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

  if (parsed.protocol !== "https:" && parsed.hostname !== "localhost") {
    throw new Error("Invalid Supabase URL protocol");
  }

  return { url, publishableKey };
}
