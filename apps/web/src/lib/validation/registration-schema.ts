import { z } from "zod";

export const registrationSchema = z
  .object({
    company_name: z.string().trim().min(2).max(160),
    owner_full_name: z.string().trim().min(2).max(160),
    owner_email: z.string().trim().email().max(320),
    password: z.string().min(8).max(128),
    confirm_password: z.string().min(8).max(128),
  })
  .refine((value) => value.password === value.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match.",
  });
