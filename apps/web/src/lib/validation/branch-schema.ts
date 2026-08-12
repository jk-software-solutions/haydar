import { z } from "zod";

export const branchSchema = z.object({
  code: z.string().trim().min(1).max(40).regex(/^[A-Za-z0-9_-]+$/).transform((value) => value.toUpperCase()),
  name: z.string().trim().min(2).max(160),
  saudi_short_address: z.preprocess(
    (value) => (typeof value === "string" && value.trim() === "" ? null : value),
    z.string().trim().max(32).nullable(),
  ),
  full_address: z.string().trim().min(3).max(1000),
  latitude: z.coerce.number().min(-90).max(90),
  longitude: z.coerce.number().min(-180).max(180),
  geofence_radius_m: z.coerce.number().int().min(20).max(10000),
  timezone: z.string().trim().min(1).max(64),
});

export const branchAssignmentSchema = z.object({
  membership_id: z.string().uuid(),
  branch_id: z.string().uuid(),
  effective_from: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  reason: z.string().trim().min(5).max(1000),
});
