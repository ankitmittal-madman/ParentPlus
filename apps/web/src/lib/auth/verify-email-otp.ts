import { verifyFounderOtp } from "../founder/auth";
import { createClient } from "../supabase/browser";

export async function verifyEmailOtp(email: string, token: string) {
  const normalizedEmail = email.trim().toLowerCase();
  const normalizedToken = token.replace(/\s/g, "");

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
    return {
      success: false,
      error: "Enter a valid email address.",
    };
  }

  if (!/^[0-9]{6}$/.test(normalizedToken)) {
    return {
      success: false,
      error: "Enter the six-digit verification code.",
    };
  }

  if (process.env.NEXT_PUBLIC_FOUNDER_MODE === "true") {
    try {
      const result = await verifyFounderOtp(normalizedEmail, normalizedToken);
      if (!result.success || !result.session) return { success: false, error: result.error };
      const { error } = await createClient().auth.setSession(result.session);
      return error ? { success: false, error: "Unable to establish the local test session." } : { success: true, error: null };
    } catch { return { success: false, error: "Unable to establish the local test session." }; }
  }

  if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true") {
    return {
      success: false,
      error: "Email verification is not enabled in this environment.",
    };
  }

  try {
    const supabase = createClient();

    const { data, error } = await supabase.auth.verifyOtp({
      email: normalizedEmail,
      token: normalizedToken,
      type: "email",
    });

    if (error || !data?.session || !data?.user) {
      return {
        success: false,
        error: "Verification failed. Check your code or request a new one.",
      };
    }

    return {
      success: true,
      error: null,
    };
  } catch {
    return {
      success: false,
      error: "Verification failed. Please try again.",
    };
  }
}
