import { expect, it } from "vitest";
import Page from "./page";
import StudentsPanel from "@/modules/families/students-panel";
import EnrollmentPanel from "@/modules/enrollments/enrollment-panel";
it("keeps invitation controls and includes the separate batch enrolment region", () => {
  const page = Page();
  expect(page.props.children[0].type).toBe(StudentsPanel);
  expect(page.props.children[1].type).toBe(EnrollmentPanel);
});
