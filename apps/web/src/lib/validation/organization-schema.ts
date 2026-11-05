import { z } from "zod";

const optionalText = (maximum: number) =>
  z.preprocess(
    (value) => (typeof value === "string" && value.trim() === "" ? null : value),
    z.string().trim().max(maximum).nullable().optional(),
  );

export const employeeProfileSchema = z.object({
  version: z.coerce.number().int().positive(),
  display_name: z.string().trim().min(2).max(160),
  commercial_registration_number: optionalText(32),
  unified_number: optionalText(32),
  employee_number: optionalText(64),
  phone: optionalText(32),
  job_title: optionalText(120),
  employment_type: z.enum(["full_time", "part_time", "contractor", "temporary"]),
  preferred_locale: z.enum(["ar", "en"]),
  attendance_enabled: z.preprocess((value) => value === "on", z.boolean()),
});

export const companySettingsSchema = z.object({
  version: z.coerce.number().int().positive(),
  display_name: z.string().trim().min(2).max(160),
  commercial_registration_number: optionalText(32),
  unified_number: optionalText(32),
  contact_phone: optionalText(32),
  tax_number: optionalText(32),
  default_locale: z.enum(["ar", "en"]),
  timezone: z.string().trim().min(1).max(64),
  country_code: z.string().trim().regex(/^[A-Za-z]{2}$/).transform((value) => value.toUpperCase()),
  attendance_biometric_policy: z.enum(["disabled", "optional", "required"]),
});
