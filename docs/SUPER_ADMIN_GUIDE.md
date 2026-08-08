# Platform owner guide

Platform access is limited to authenticated emails listed in `PLATFORM_ADMIN_EMAILS`. A normal
company owner cannot become a platform administrator through an API payload.

The platform portal shows company, employee, branch, trial, and subscription counts. From it, the
platform owner can change a company status or plan, manage coupons, start time-limited support
mode, and update platform settings. Every privileged mutation creates a platform audit entry.

Support mode is for troubleshooting only. Confirm customer authorization, set the shortest useful
expiry, ensure the visible support banner is present, avoid unnecessary employee records, and end
the session immediately after the investigation. Never impersonate silently.

Manual subscription activation must include the intended plan, billing cycle, dates, and an
operator note. Payment-provider status deliberately reports `not_configured` until a provider is
chosen and implemented; do not represent a manual activation as a successful card payment.

Before suspending a company, confirm identity and business authorization, preserve the audit trail,
and communicate impact. Database access is not a substitute for platform actions except during a
documented recovery incident.
