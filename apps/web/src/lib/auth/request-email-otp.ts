import { createClient } from "../supabase/browser";

export async function requestEmailOtp(email: string) {
  const normalizedEmail = email.trim().toLowerCase();

  if (
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)
  ) {
    return {
      success: false,
      error: "Enter a valid email address.",
    };
  }

  if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true") {
    return {
      success: false,
      error: "Email verification is not enabled in this environment.",
    };
  }

  try {
    const supabase = createClient();

    const { error } = await supabase.auth.signInWithOtp({
      email: normalizedEmail,
      options: {
        shouldCreateUser: false,
      },
    });

    if (error) {
      return {
        success: false,
        error: "Unable to send verification code. Please try again.",
      };
    }

    return {
      success: true,
      error: null,
    };
  } catch {
    return {
      success: false,
      error: "Unable to send verification code. Please try again.",
    };
  }
}
