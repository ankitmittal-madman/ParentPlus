import { expect, it, vi } from "vitest";
const client = vi.hoisted(() => vi.fn());
vi.mock("@supabase/supabase-js", () => ({ createClient: client }));
import { createFounderAdmin } from "./server-admin";
it("uses the server credential without enabling persisted admin sessions", async () => {
  client.mockReturnValue({ auth: {} });
  await createFounderAdmin({ url: "https://fmavpazczahxeusqbxuh.supabase.co", publishableKey: "public", serviceKey: "server-only", mode: "hosted-testing", projectRef: "fmavpazczahxeusqbxuh" });
  expect(client).toHaveBeenCalledWith("https://fmavpazczahxeusqbxuh.supabase.co", "server-only", { auth: { persistSession: false, autoRefreshToken: false } });
});
