import { z } from "zod";

export const invitationSchema = z
  .object({
    full_name: z.string().trim().min(2).max(160),
    email: z.email().trim().toLowerCase(),
    role_code: z.enum(["MANAGER", "SUPERVISOR", "HR_OFFICER", "EMPLOYEE"]),
  })
  .strict();

export type InvitationInput = z.infer<typeof invitationSchema>;
