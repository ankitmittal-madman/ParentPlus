import { connection } from "next/server";
import ClassRecoveryPanel from "./class-recovery-panel";

// Read the server-only flag per request rather than during static prerendering.
export default async function ClassRecoveryGate() {
  await connection();
  return process.env.PARENTPLUS_ENABLE_CLASS_SETUP === "true" ? <ClassRecoveryPanel /> : null;
}
