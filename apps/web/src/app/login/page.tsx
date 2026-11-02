"use client";

import { useState, type FormEvent } from "react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalized = email.trim().toLowerCase();

    if (
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized)
    ) {
      setError("Enter a valid email address.");
      setSubmitted(false);
      return;
    }

    setError("");
    setEmail(normalized);
    setSubmitted(true);
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-5 py-10">
      <section className="w-full max-w-md rounded-3xl bg-white p-7 shadow-sm">
        <div
          aria-hidden="true"
          className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand text-2xl text-white"
        >
          ✦
        </div>

        <h1 className="text-2xl font-bold text-ink">
          Welcome to Parent Plus
        </h1>

        <p className="mt-2 text-sm leading-6 text-muted">
          Sign in with your email to continue.
        </p>

        <form onSubmit={handleSubmit} noValidate className="mt-8 space-y-5">
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-semibold text-ink"
            >
              Email address
            </label>

            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setError("");
                setSubmitted(false);
              }}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? "email-error" : undefined}
              placeholder="you@example.com"
              className="w-full rounded-xl border border-gray-300 px-4 py-3 text-base text-ink outline-none focus-visible:ring-2 focus-visible:ring-brand"
            />

            {error && (
              <p id="email-error" role="alert" className="mt-2 text-sm text-red-700">
                {error}
              </p>
            )}
          </div>

          <button
            type="submit"
            className="w-full rounded-xl bg-brand px-5 py-3 font-semibold text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            Continue
          </button>
        </form>

        {submitted && (
          <p role="status" className="mt-5 text-sm text-muted">
            Email accepted. OTP delivery will be enabled in the next step.
          </p>
        )}
      </section>
    </main>
  );
}
