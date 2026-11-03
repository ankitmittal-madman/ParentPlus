import type { AuthChangeEvent } from "@supabase/supabase-js";
import { createClient } from "../supabase/browser";

export function observeSessionChanges(onChange: (event: AuthChangeEvent) => void): () => void {
  if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true") return () => {};
  const { data: { subscription } } = createClient().auth.onAuthStateChange((event) => {
    if (event !== "INITIAL_SESSION") onChange(event);
  });
  return () => subscription.unsubscribe();
}
