# Company administrator guide

## First setup

Register the company owner, then complete the company settings. Create departments, branches,
and shifts before inviting employees. Every branch needs coordinates, a timezone, and a geofence
radius. Assign each attendance-enabled employee to an active branch and either an employee or
branch shift.

## Employees and devices

Invite employees with the least-privileged role. The first Android installation registered by an
employee becomes the approved device. A replacement device stays pending until an authorized
manager reviews the reason; approval revokes the previous device. Do not share employee accounts.

## Attendance

Employees can check in and out through GPS or a current branch QR token. The server—not the
phone—validates subscription, company/member status, device, assignment, schedule, token, and
distance. Local fingerprint/face unlock is only an optional device confirmation.

Managers may enter or correct attendance only with a reason. These changes retain old/new values
in audit history. The five-minute maintenance job flags sessions left open more than two hours
after scheduled end. Review `missing_checkout` and unauthorized early-departure records promptly.

## Workforce operations

- Assign tasks to one or more employees or an active branch, monitor list/Kanban status, extend due
  dates, reassign, and review comments or evidence attachments.
- Review permission and leave requests with a written comment where useful. Approved leave reduces
  the employee's annual balance and affects attendance.
- Review uploaded employee documents and act on in-app expiration alerts.
- Generate filtered reports and download exports only from the authenticated company portal.
- In **Report center**, combine employee, branch, department, group, period, and status filters;
  configure ranking visibility/anonymization separately. Report downloads expire after seven days,
  so regenerate an expired export rather than sharing a stale link.

## Security routine

Review pending devices, manual attendance, platform support banners, role assignments, expired
documents, and audit logs. Remove access when employment ends. Never send passwords, refresh
tokens, signing keys, or exported employee data through unapproved channels.

Employee phone login uses a strict international number such as `+966500000000`. Saving a unique
phone in the employee editor marks it administrator-verified and enables that identifier with the
employee's existing password; clearing it disables phone login. Deactivating a membership revokes
its sessions and devices immediately. Reactivation requires a new login and does not restore device
approval.

Operational-group membership is managed from the group section and affects scoped tasks, Proof of
Presence, reports and manager visibility. Branch details can be edited with optimistic versioning.
Company owners can open **Roles and access** from the Flutter More tab to edit member roles,
allow/deny permission overrides, and branch/department/group scope. Actors with
`departments:manage` can open **Operational groups** there to create, edit, activate/deactivate,
and replace group membership.
The branch editor only offers owner/manager-role members as the branch manager and supports multiple
supervisor-role members. Saving either branch details or supervisors refreshes the shared branch
version; reload after a concurrency warning before retrying.
QR controls distinguish creation from rotation: rotation invalidates all prior active tokens for the
selected branch. Use explicit revoke if a displayed token may have been exposed.
The company settings biometric policy can be disabled, optional, or required. Use required only
after confirming every attendance device has enrolled biometrics; unsupported, unenrolled,
cancelled, or locked-out devices cannot submit attendance while required mode is active.
