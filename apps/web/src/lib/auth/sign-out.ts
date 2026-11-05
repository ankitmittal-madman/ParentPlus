import { createClient } from "../supabase/browser";

export async function signOut() {
  const failure = { success: false, error: "Unable to confirm sign-out. Please try again." };
  if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true") return failure;

  try {
    const { error } = await createClient().auth.signOut({ scope: "local" });
    return error ? failure : { success: true, error: null };
  } catch {
    return failure;
  }
}
