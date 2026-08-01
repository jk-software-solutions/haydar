import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import arabic from "@/i18n/messages/ar.json";
import english from "@/i18n/messages/en.json";

import { FoundationContent } from "./foundation-content";

describe("FoundationContent", () => {
  it("renders Arabic content and links to English", () => {
    render(<FoundationContent locale="ar" dictionary={arabic} />);

    expect(screen.getByRole("heading", { name: "حضور أوضح، وإدارة أسهل" })).toBeVisible();
    expect(screen.getByRole("link", { name: "English" })).toHaveAttribute("href", "/en");
    expect(screen.getByRole("link", { name: "تسجيل الدخول" })).toHaveAttribute("href", "/ar/login");
  });

  it("renders English content and links to Arabic", () => {
    render(<FoundationContent locale="en" dictionary={english} />);

    expect(screen.getByRole("heading", { name: "Attendance, clearly managed" })).toBeVisible();
    expect(screen.getByRole("link", { name: "العربية" })).toHaveAttribute("href", "/ar");
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/en/login");
  });
});
