// The founder explicitly selected this existing project as the testing backend.
// Project references and the public anon key are not server credentials.
export const FOUNDER_TEST_PROJECT_REF = "fmavpazczahxeusqbxuh";
export function isFounderTestBackend(url: string, projectRef: string | undefined) {
  return projectRef === FOUNDER_TEST_PROJECT_REF && url === `https://${FOUNDER_TEST_PROJECT_REF}.supabase.co`;
}
