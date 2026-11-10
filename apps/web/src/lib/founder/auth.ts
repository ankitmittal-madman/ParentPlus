"use server";
import { createClient } from "@supabase/supabase-js";
import { createFounderAdmin } from "./server-admin";
import { founderConfig } from "./runtime";
const synthetic = (email: string) => /^[^\s@]+@[^\s@]+\.test$/.test(email);
const denied = { success: false, error: "Founder sign-in is unavailable. Use a fictional .test email and code 123456 in the configured founder testing app." } as const;
export async function requestFounderOtp(email: string) {
  return founderConfig() && synthetic(email) ? { success: true, error: null } : denied;
}
export async function verifyFounderOtp(email: string, code: string) {
  const config = founderConfig();
  if (!config || !synthetic(email) || code !== "123456") return { ...denied, session: null };
  try {
    const options = { auth: { persistSession: false, autoRefreshToken: false } };
    const admin = await createFounderAdmin(config);
    const link = await admin.auth.admin.generateLink({ type: "magiclink", email });
    const hash = link.data?.properties?.hashed_token;
    if (link.error || !hash) return { ...denied, session: null };
    const client = createClient(config.url, config.publishableKey, options);
    const result = await client.auth.verifyOtp({ type: "email", token_hash: hash });
    if (result.error || !result.data.session || !result.data.user) return { ...denied, session: null };
    return { success: true, error: null, session: { access_token: result.data.session.access_token, refresh_token: result.data.session.refresh_token } };
  } catch { return { ...denied, session: null }; }
}
