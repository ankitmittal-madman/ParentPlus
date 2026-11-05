import { isAuthSessionMissingError } from "@supabase/supabase-js";
import { createClient } from "../supabase/browser";

type SessionStatus = { state: "signed-in" | "signed-out" | "unavailable" };

export async function getSessionStatus(): Promise<SessionStatus> {
  if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true") return { state: "signed-out" };
  try {
    const { data, error } = await createClient().auth.getUser();
    if (error) return { state: isAuthSessionMissingError(error) ? "signed-out" : "unavailable" };
    return { state: data?.user?.id ? "signed-in" : "unavailable" };
  } catch {
    return { state: "unavailable" };
  }
}
