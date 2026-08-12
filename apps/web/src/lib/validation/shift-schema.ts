import { z } from "zod";

export const shiftSchema = z.object({
  code: z.string().trim().min(1).max(40).regex(/^[A-Za-z0-9_-]+$/).transform((value) => value.toUpperCase()),
  name: z.string().trim().min(2).max(160),
  start_time: z.string().regex(/^([01]\d|2[0-3]):[0-5]\d$/),
  end_time: z.string().regex(/^([01]\d|2[0-3]):[0-5]\d$/),
  working_days: z.array(z.coerce.number().int().min(0).max(6)).min(1).max(7).refine((days) => new Set(days).size === days.length),
  grace_period_minutes: z.coerce.number().int().min(0).max(240),
  break_duration_minutes: z.coerce.number().int().min(0).max(720),
  effective_from: z.iso.date(),
  effective_to: z.preprocess(
    (value) => (value === "" ? null : value),
    z.iso.date().nullable(),
  ),
}).refine(
  (value) => value.effective_to === null || value.effective_to >= value.effective_from,
  { path: ["effective_to"], message: "End date must not precede start date" },
);

export const shiftAssignmentSchema = z.object({
  shift_id: z.string().uuid(),
  target_type: z.enum(["branch", "employee"]),
  membership_id: z.preprocess(
    (value) => (value === "" ? null : value),
    z.string().uuid().nullable(),
  ),
  branch_id: z.preprocess(
    (value) => (value === "" ? null : value),
    z.string().uuid().nullable(),
  ),
  effective_from: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  effective_to: z.preprocess(
    (value) => (value === "" ? null : value),
    z.string().regex(/^\d{4}-\d{2}-\d{2}$/).nullable(),
  ),
}).refine(
  (value) => value.effective_to === null || value.effective_to >= value.effective_from,
  { path: ["effective_to"], message: "End date must not precede start date" },
).refine(
  (value) => (
    value.target_type === "employee"
      ? value.membership_id !== null && value.branch_id === null
      : value.branch_id !== null && value.membership_id === null
  ),
  { path: ["target_type"], message: "Choose either one employee or one branch" },
);
