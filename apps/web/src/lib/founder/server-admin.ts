import { createClient } from "@supabase/supabase-js";
import type { founderConfig } from "./runtime";
export async function createFounderAdmin(config: NonNullable<ReturnType<typeof founderConfig>>) {
  const admin = createClient(config.url, config.serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
  return admin;
}
