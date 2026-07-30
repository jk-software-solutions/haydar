# HADIR | حاضر — Master Codex Implementation Prompt

## Your role

Act as a senior solution architect, Flutter engineer, FastAPI engineer, Next.js engineer, DevOps engineer, QA engineer, and security reviewer.

Your task is to plan and build **HADIR | حاضر**, a production-oriented multi-tenant SaaS platform for employee attendance, shifts, branches, tasks, leave, documents, reports, subscriptions, and company management.

Work incrementally and verify every claim. Do not create demo-only screens, disconnected mock pages, or multiple mobile applications.

---

## Final decisions

1. **No Figma phase.** Build the UI directly in Flutter and Next.js using reusable design tokens and components.
2. **One Flutter mobile app only.** The same app supports Employee, Manager, Supervisor, HR, and Company Owner roles. Navigation and permissions change according to the authenticated role.
3. **One responsive web portal** containing:
   - Company Admin area.
   - Platform Super Admin area.
4. **Delivery target: 30 calendar days.** The implementation, Android release build, documentation, and Google Play submission package must be ready by Day 30. Store review time is external.
5. **Arabic and English from the beginning**, with correct RTL/LTR behavior and architecture ready for additional languages.
6. **The backend is the source of truth** for tenant isolation, attendance rules, permissions, device binding, subscriptions, and audit logs.

---

## Product vision

HADIR is initially used by one company but must be built as a commercial SaaS product that can be sold to many companies through monthly or annual subscriptions.

Every company has isolated data for:

- Employees and managers.
- Branches and departments.
- Shifts.
- Attendance.
- Tasks.
- Leave balances and requests.
- Employee documents.
- Reports.
- Subscription and usage limits.
- Company settings.
- Audit logs.

---

## Roles and permissions

Implement these roles:

### Platform

- `SUPER_ADMIN`: manages companies, plans, subscriptions, coupons, support, and system settings. Any support access to a company must be visible and audited.

### Company

- `COMPANY_OWNER`
- `COMPANY_MANAGER`
- `SUPERVISOR`
- `HR_OFFICER`
- `EMPLOYEE`

Use granular permissions with actions:

- View
- Create
- Edit
- Delete
- Approve
- Export
- Manage

Permission domains:

- Employees
- Branches
- Shifts
- Attendance
- Manual attendance
- Tasks
- Leave
- Documents
- Reports
- Roles
- Subscription
- Company settings
- Audit logs

---

# Mandatory MVP scope

## 1. Authentication and activation

Implement:

- Email or phone login.
- Password authentication.
- Password reset.
- OTP-ready architecture.
- Company registration.
- Employee invitation and activation.
- Join company using invitation link or code.
- Role-based routing.
- Access and refresh tokens.
- Session revocation.
- Secure logout.
- Account activation/deactivation.
- Trial account state.

Never store privileged secrets or business rules in the mobile app.

## 2. Multi-tenancy

Use PostgreSQL with strict tenant scoping.

Every company-owned row must include `company_id`.

Enforce isolation in:

- API dependencies.
- Services.
- Repositories.
- Database queries.
- Background jobs.
- Exports.
- File storage paths.

Never trust a `company_id` supplied by the client. Resolve it from the authenticated session.

Add automated tests proving that one company cannot access another company’s records.

## 3. One approved device per employee

Implement:

- Device registration on activation.
- Secure app-generated installation ID.
- Backend device validation for sensitive actions.
- Unauthorized-device state.
- Device-change request.
- Manager approval or new activation link.
- Old-device revocation.
- Device history.
- Audit logs.

Prepare an integration point for Google Play Integrity. Do not depend on a single unstable hardware identifier.

## 4. Branches

Implement:

- Multiple branches.
- Branch name and code.
- Saudi short address.
- Full address.
- Latitude and longitude.
- Geofence radius.
- Time zone.
- Working hours.
- Branch manager.
- Assigned employees.
- Active/inactive status.
- Employee transfer history.

Provide a map picker and manual address fields.

## 5. Shifts

Implement:

- Multiple shifts.
- Name.
- Start/end time.
- Overnight shifts.
- Working days.
- Grace period.
- Break duration.
- Effective date range.
- Assigned branches and employees.
- Recurrence.
- Exceptions.
- Active/inactive status.
- Overlap validation.

## 6. Attendance

Support:

- GPS/geofence attendance.
- QR attendance.
- Approved-device validation.
- Optional device biometric confirmation using the phone’s secure biometric API.

Store:

- Employee.
- Company.
- Branch.
- Shift.
- Check-in/check-out times.
- Coordinates.
- Distance from branch.
- Attendance method.
- Device.
- Status.
- Late duration.
- Early-departure duration.
- Approval information.
- Manual-edit metadata.

Statuses:

- On time.
- Late.
- Absent.
- Approved leave.
- Approved permission.
- Early departure.
- Manual attendance.
- Pending review.
- Missing check-out.

Backend validation must check:

- Active company subscription.
- Employee status.
- Assigned branch and shift.
- Allowed time window.
- Geofence.
- Approved device.
- Duplicate check-in.
- Existing open attendance session.
- Early-departure approval when required.

Never trust a client-calculated distance or attendance status.

## 7. Manual attendance

Authorized managers can add or correct attendance.

Require:

- Employee.
- Date.
- Branch.
- Check-in/check-out.
- Mandatory reason.
- Optional attachment.
- Confirmation.

Audit who changed it, previous and new values, time, reason, and session metadata. Clearly label manual records.

## 8. Early departure and hourly permission

Employees can request:

- One hour.
- Multiple hours.
- Custom time range.
- Until end of shift.

Workflow:

1. Employee submits request.
2. Manager receives notification.
3. Manager approves/rejects with comment.
4. Approved permission affects attendance validation.
5. Unapproved departure is recorded as unauthorized.

The system cannot physically prevent leaving; it records and classifies the event.

## 9. Proof of Presence

Managers can send a request to one employee, multiple employees, a branch, or a group.

Options:

- Deadline.
- Location verification.
- Optional QR confirmation placeholder.
- Optional future selfie placeholder.
- Message.

Results:

- Verified.
- Outside branch.
- No response.
- Technical issue.
- Pending review.

Do not implement advanced server-side face recognition in the 30-day MVP.

## 10. Tasks with chat-like updates

Implement:

- Personal, group, and branch tasks.
- Title and description.
- Priority.
- Due date.
- Assignee.
- Attachments.
- Chat-like comments.
- Read receipts.
- Status history.
- Request-more-time flow.

Statuses:

- New.
- Viewed.
- In progress.
- Completed.
- Postponed.
- Needs more time.
- Blocked.

Employees can update status, comment, upload completion proof, and request more time. Managers can assign, reassign, extend deadlines, and review completion.

## 11. Leave

Implement:

- Leave types.
- Annual allowance.
- Used and remaining balance.
- Leave requests.
- Date range.
- Reason and attachment.
- Approval workflow.
- Manager comment.
- Balance adjustment with audit log.
- Approved leave reflected in attendance.

## 12. Employee documents

Support:

- Iqama.
- Passport.
- Medical insurance.
- Employment contract.
- Driver’s license.
- Vehicle insurance.
- Custom types.

Store document number, issue date, expiry date, attachment, reminder schedule, and status.

Statuses:

- Valid.
- Expiring soon.
- Expired.
- Missing.
- Pending review.

Create scheduled expiry notifications.

## 13. Reports and exports

Reports:

- Attendance.
- Absence.
- Lateness.
- Early departure.
- Worked hours.
- Leave.
- Permissions.
- Tasks.
- Expiring documents.
- Branch, shift, and employee summaries.

Filters:

- Date range.
- Employee.
- Branch.
- Department.
- Shift.
- Status.

Exports:

- PDF.
- Excel/XLSX.

Generate exports on the server and enforce tenant isolation.

## 14. Attendance ranking

Optional company feature:

- First, second, and third arrival.
- Weekly consistency.
- On-time streak.

Visibility:

- Manager only.
- Branch.
- Company.
- Disabled.

Avoid public shaming of late or absent employees.

## 15. Plans, subscriptions, coupons, and limits

Implement:

- Free trial.
- Basic, Professional, and Enterprise plans.
- Monthly/annual periods.
- Coupons.
- Trial extension.
- Manual subscription activation.
- Renewal/expiry dates.
- Company suspension.
- Upgrade/downgrade architecture.
- Usage limits.

Limits can include:

- Employees.
- Branches.
- Storage.
- Reports.
- Attendance methods.
- Task features.
- Document management.
- Support level.

If no payment gateway is selected, do not fake it. Create a provider adapter interface and implement manual/test activation only.

## 16. Notifications

Use Firebase Cloud Messaging plus in-app notifications.

Support:

- New tasks and deadlines.
- Proof of presence.
- Approval/rejection.
- Late attendance.
- Missing check-out.
- Document expiry.
- Shift change.
- Branch transfer.
- Device change.
- Leave update.
- Subscription expiry.

## 17. Localization

Implement Arabic and English using translation keys, not hardcoded strings.

Requirements:

- Full RTL/LTR switching.
- Locale-aware dates and numbers.
- Additional languages can be added later.
- Arabic font such as Cairo, Tajawal, or IBM Plex Sans Arabic.
- English font such as Inter.

---

# Outside the core 30-day MVP

Do not silently include these:

1. Advanced face recognition.
2. Payroll and salary calculation.
3. Deep biometric identity verification.
4. Live payment gateway before provider selection.
5. Native iOS App Store publication.
6. Full offline-first sync for all modules.
7. ERP/HR third-party integrations.
8. WhatsApp integration.
9. AI features.
10. Large CMS marketing website.

Keep Flutter cross-platform, but Android and Google Play are the Day 30 target.

---

# Required stack

## Mobile

- Flutter stable.
- Dart stable.
- Material 3.
- Riverpod.
- GoRouter.
- Dio.
- Freezed/json_serializable.
- Flutter Secure Storage.
- Geolocator.
- Google Maps Flutter.
- Mobile Scanner.
- Local Auth.
- Firebase Messaging.
- Flutter Local Notifications.
- Intl/localization.

Feature-first structure:

```text
apps/mobile/lib/
  app/
  core/
  shared/
  features/
    auth/
    company/
    employees/
    branches/
    shifts/
    attendance/
    permissions/
    proof_of_presence/
    tasks/
    leave/
    documents/
    notifications/
    reports/
    subscriptions/
    profile/
```

## Backend

- Python 3.12.
- FastAPI.
- Pydantic v2.
- SQLAlchemy 2.
- Alembic.
- PostgreSQL.
- Async database access.
- JWT access/refresh tokens.
- Argon2 or another modern password hash.
- Redis only where justified.
- Background jobs only where required.
- Pytest.
- Ruff.
- Mypy where practical.

Structure:

```text
services/api/app/
  api/
  core/
  db/
  models/
  schemas/
  repositories/
  services/
  policies/
  tasks/
  integrations/
  tests/
```

## Web portal

- Next.js with TypeScript.
- App Router.
- Tailwind CSS.
- TanStack Query.
- React Hook Form.
- Zod.
- Arabic/English i18n.
- Responsive Company Admin and Super Admin layouts.

## Infrastructure

- Docker and Docker Compose.
- PostgreSQL container.
- Optional Redis container.
- API and web containers.
- Environment-based configuration.
- GitHub Actions for lint, tests, and builds.
- S3-compatible storage abstraction for attachments.

---

# Repository rules

Before editing:

1. Inspect the full repository.
2. Detect whether it is empty, partial, or already structured.
3. Read README, package, environment, Docker, and CI files.
4. Preserve useful code.
5. Do not delete unrelated files.
6. Do not initialize a nested Git repository.
7. Confirm repository root, branch, and Git status.
8. Check Flutter, Dart, Python, Node, Docker, and Git versions.
9. Check disk space before large installs.
10. Record assumptions and risks.

If empty, create:

```text
hadir/
  apps/
    mobile/
    web/
  services/
    api/
  docs/
  infrastructure/
  scripts/
  .github/
  README.md
  docker-compose.yml
  .env.example
```

---

# Mandatory planning documents

Create or update before major implementation:

1. `docs/IMPLEMENTATION_PLAN.md`
2. `docs/ARCHITECTURE.md`
3. `docs/DATA_MODEL.md`
4. `docs/API_SPEC.md`
5. `docs/SECURITY.md`
6. `docs/TEST_PLAN.md`
7. `docs/DEPLOYMENT.md`
8. `docs/ASSUMPTIONS_AND_RISKS.md`

The plan must include repository status, confirmed scope, exclusions, architecture, data model, API groups, security, schedule, acceptance criteria, risks, credentials needed, and the first milestone.

Ask only true blocking questions. Document reasonable assumptions and continue.

---

# Core database model

Design normalized models for at least:

### Identity and tenancy

- users
- user_sessions
- companies
- company_memberships
- roles
- permissions
- role_permissions
- membership_roles
- invitations
- devices
- device_change_requests

### Organization

- branches
- departments
- employee_profiles
- employee_branch_history
- shifts
- shift_assignments
- shift_exceptions

### Attendance

- attendance_records
- attendance_events
- attendance_corrections
- qr_tokens
- proof_of_presence_requests
- proof_of_presence_responses
- permission_requests
- permission_approvals

### Tasks

- tasks
- task_assignees
- task_comments
- task_attachments
- task_status_history
- task_read_receipts

### Leave and documents

- leave_types
- leave_balances
- leave_requests
- leave_approvals
- employee_documents
- document_types
- document_reminders

### Notifications and reports

- notifications
- notification_preferences
- export_jobs
- audit_logs

### SaaS billing

- plans
- plan_features
- subscriptions
- subscription_events
- coupons
- coupon_redemptions
- usage_counters

Use UUIDs unless justified otherwise. Add timestamps, soft-delete fields where appropriate, and optimistic locking where race conditions matter.

---

# API groups

Create versioned REST APIs under `/api/v1`:

- `/auth`
- `/companies`
- `/memberships`
- `/roles`
- `/permissions`
- `/employees`
- `/devices`
- `/branches`
- `/shifts`
- `/attendance`
- `/attendance/manual`
- `/attendance/history`
- `/permission-requests`
- `/proof-of-presence`
- `/tasks`
- `/leave`
- `/documents`
- `/notifications`
- `/reports`
- `/exports`
- `/plans`
- `/subscriptions`
- `/coupons`
- `/super-admin`
- `/support-mode`
- `/audit-logs`
- `/health`

Use consistent pagination, filtering, sorting, validation, error responses, idempotency, authorization, and rate limiting. Generate OpenAPI docs.

---

# UI without Figma

Build a coherent design system directly in code:

- Color tokens.
- Typography.
- Spacing.
- Radius.
- Shadows.
- Buttons.
- Inputs.
- Cards.
- Status badges.
- Dialogs.
- Bottom sheets.
- Empty/error/loading states.
- Tables and charts.
- Notifications.
- Upload components.
- Date/time pickers.

Visual direction:

- Modern Saudi SaaS.
- Professional, friendly, and accessible.
- Deep emerald/teal primary.
- Professional blue secondary.
- Orange warning accent.
- Soft neutral backgrounds.
- Strong Arabic typography.
- Minimal visual noise.
- Large touch targets.
- Correct RTL.

Mobile navigation:

### Employee

- Home
- Attendance
- Tasks
- Requests
- Profile

### Manager/Supervisor

- Dashboard
- Team
- Attendance
- Tasks
- More

Do not expose manager features to employees.

---

# Required screens

## Mobile shared

- Splash.
- Language selection.
- Onboarding.
- Login.
- Forgot password.
- Invitation activation.
- Device activation.
- Unauthorized device.
- Notifications.
- Profile/settings.
- Offline and error states.

## Employee

- Home.
- Current shift.
- Check-in/check-out.
- GPS verification.
- QR scanner.
- Biometric confirmation.
- Attendance history.
- Permission request.
- Proof of presence.
- Tasks and task conversation.
- Leave balance/request.
- Documents and expiry reminders.

## Manager/Supervisor

- Dashboard.
- Live team status.
- Employee list/details.
- Manual attendance.
- Approval center.
- Proof-of-presence management.
- Task creation/management.
- Branches.
- Shifts.
- Reports and exports.
- Subscription usage.

## Company Admin web

- Dashboard.
- Employees.
- Branches.
- Shifts.
- Attendance.
- Live attendance.
- Manual attendance.
- Approvals.
- Tasks.
- Leave.
- Documents.
- Reports.
- Exports.
- Roles and permissions.
- Subscription and usage.
- Company settings.
- Audit logs.
- Notifications.

## Super Admin web

- Platform dashboard.
- Companies.
- Company details.
- Plans.
- Subscriptions.
- Coupons.
- Usage.
- Support.
- Audit logs.
- Suspicious activity.
- Announcements.
- Platform settings.
- Audited support-mode entry.

---

# Security requirements

Implement:

- Strong password hashing.
- Short-lived access tokens.
- Refresh-token revocation.
- Tenant-scoped authorization.
- RBAC and policy checks.
- Rate limiting.
- Input validation.
- File type/size validation.
- Private file storage.
- Signed file URLs.
- Audit logs.
- Sensitive-action confirmations.
- No secrets in source control.
- CORS restrictions.
- Secure headers.
- Idempotency for attendance and subscription events.
- Device revocation.
- Support-access logging.
- Backup documentation.
- Google Play Integrity integration point.
- Flutter release obfuscation where supported.

The APK is not the security boundary; the backend is authoritative.

---

# Testing

## Backend

- Unit and service tests.
- Policy tests.
- Multi-tenant isolation tests.
- Attendance validation tests.
- Overnight shift tests.
- Subscription limit tests.
- Approval workflow tests.
- Export authorization tests.
- API integration tests.

## Mobile

- Critical widget/state tests.
- Authentication flow.
- Attendance flow.
- Location-permission states.
- Device-authorization states.
- RTL smoke tests.

## Web

- Form validation.
- Route guards.
- Permission visibility.
- RTL smoke tests.

## Required end-to-end flows

1. Company registers.
2. Owner adds branch and shift.
3. Owner invites employee.
4. Employee activates one device.
5. Employee checks in inside geofence.
6. Outside-geofence check-in fails.
7. Manager approves early departure.
8. Employee checks out with approval.
9. Manager sends proof of presence.
10. Employee responds.
11. Manager creates task.
12. Employee completes task with attachment.
13. HR approves leave.
14. Report exports to PDF and Excel.
15. Super Admin creates plan and activates subscription.
16. Cross-company access is blocked.

---

# 30-day execution plan

## Days 1–3: Audit and foundation

### Day 1

- Audit repository and environment.
- Confirm root, branch, status, and existing code.
- Create planning documents.
- Finalize MVP and exclusions.
- Finalize architecture, data model, API groups, risks, and blockers.

### Day 2

- Create monorepo structure.
- Configure formatting/linting.
- Configure Docker Compose and PostgreSQL.
- Scaffold FastAPI, Flutter, and Next.js.
- Create `.env.example`.

### Day 3

- Shared design tokens.
- Arabic/English localization foundations.
- Backend configuration and database connection.
- Base models and migrations.
- Health checks.
- Initial CI.

## Days 4–7: Authentication, tenancy, roles, devices

### Day 4

- Users, companies, memberships.
- Login, refresh, logout.
- Password hashing.
- Authorization dependencies.

### Day 5

- Invitations and activation.
- Roles and permissions.
- Company owner workflow.
- Super Admin bootstrap.

### Day 6

- Device registration and validation.
- Device-change requests.
- Revocation and history.
- Mobile activation screens.

### Day 7

- Company settings.
- Employee profiles.
- Role-aware mobile navigation.
- Company Admin employee list.
- Tenant-isolation tests.

## Days 8–10: Branches and shifts

### Day 8

- Branch CRUD.
- Coordinates and radius.
- Saudi short address.
- Assignment and transfer history.

### Day 9

- Shift CRUD.
- Overnight shifts.
- Grace periods and working days.
- Assignments and conflicts.

### Day 10

- Employee branch/shift assignment UI.
- Mobile manager screens.
- Web branch/shift screens.
- Tests.

## Days 11–14: Attendance

### Day 11

- Attendance models and validation service.
- Check-in endpoint.
- Open-session and duplicate prevention.
- Employee attendance home state.

### Day 12

- Check-out.
- Late/early calculations.
- Missing check-out.
- Attendance history.

### Day 13

- Server geofence validation.
- Mobile GPS flow.
- Outside-area, denied-permission, and disabled-location states.

### Day 14

- QR generation/validation.
- QR scanner.
- Approved-device enforcement.
- Local biometric confirmation.

## Days 15–17: Manual attendance, permissions, proof of presence

### Day 15

- Manual attendance and corrections.
- Mandatory reason.
- Before/after audit log.
- Mobile/web manager interfaces.

### Day 16

- Hourly and early-departure requests.
- Approval workflow.
- Notifications.
- Attendance integration.

### Day 17

- Proof-of-presence request, deadline, response, verification, tracking, and results.

## Days 18–20: Tasks

### Day 18

- Task models.
- Create/assign personal, group, and branch tasks.
- Statuses.
- Mobile inbox.

### Day 19

- Chat-like comments.
- Attachments.
- Read receipts.
- Status history.
- Request-more-time flow.

### Day 20

- Manager task board.
- Company Admin task views.
- Notifications, filters, and tests.

## Days 21–22: Leave and documents

### Day 21

- Leave types, balances, requests, approvals, attendance integration.

### Day 22

- Documents, custom types, expiry statuses, reminders, mobile/web screens.

## Days 23–24: Reports and exports

### Day 23

- Attendance, absence, lateness, early departure, worked-hours reports and filters.

### Day 24

- Leave, permission, task, and document reports.
- PDF/Excel exports.
- Export jobs and authorization tests.

## Days 25–26: Plans and Super Admin

### Day 25

- Plans, features, limits, coupons, trial, manual activation, subscription middleware.

### Day 26

- Super Admin dashboard.
- Company management.
- Suspend/reactivate.
- Trial extension.
- Plan changes.
- Support mode.

## Day 27: Localization and UI refinement

- Finish Arabic/English.
- RTL review.
- Attendance ranking and visibility.
- Empty/loading/error states.
- Accessibility review.

## Day 28: Security and integration testing

- Security review.
- Multi-tenant and permission tests.
- Rate limiting.
- File validation.
- Audit review.
- End-to-end flows.
- Fix critical bugs.

## Day 29: Deployment and release preparation

- Production Docker setup.
- Migration and backup procedures.
- API/web deployment.
- Domain/SSL documentation.
- Firebase setup.
- Android signing.
- AAB release build.
- Play Store checklist.

## Day 30: Final QA and handoff

- Real-device Android testing.
- Arabic/English regression pass.
- Final APK/AAB and web build.
- Source code and documentation.
- Admin and deployment guides.
- Known limitations.
- Google Play submission package.
- Final handoff summary.

---

# Acceptance criteria

The MVP is accepted only when:

1. One Flutter app supports employee and manager/supervisor roles.
2. Company data is tenant-isolated.
3. Branches and shifts work.
4. Employees can be assigned to branches and shifts.
5. One-device activation works.
6. GPS/geofence attendance works.
7. QR attendance works.
8. Manual attendance produces an audit trail.
9. Permission and early-departure workflows work.
10. Proof of Presence works.
11. Tasks support comments and attachments.
12. Leave balances and requests work.
13. Documents and expiry reminders work.
14. Reports export to PDF and Excel.
15. Plans, limits, coupons, and subscriptions are manageable.
16. Super Admin manages companies and subscriptions.
17. Arabic and English work correctly.
18. Critical flows are tested.
19. Docker local startup works.
20. Android release build succeeds.
21. Source code and documentation are complete.

---

# Required handoff documentation

Provide:

- Root `README.md`.
- Local setup guide.
- Environment guide.
- Migration guide.
- Docker guide.
- Deployment guide.
- Google Play release guide.
- Firebase and Google Maps setup.
- Company Admin guide.
- Super Admin guide.
- Backup/restore guide.
- API documentation.
- Security notes.
- Known limitations.
- Future roadmap.
- Test report.

Create `.env.example` with placeholders for:

```env
APP_ENV=
APP_NAME=HADIR
API_BASE_URL=
DATABASE_URL=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
JWT_SECRET=
JWT_ACCESS_TOKEN_MINUTES=
JWT_REFRESH_TOKEN_DAYS=
CORS_ORIGINS=
REDIS_URL=
STORAGE_PROVIDER=
STORAGE_BUCKET=
STORAGE_ENDPOINT=
STORAGE_ACCESS_KEY=
STORAGE_SECRET_KEY=
FIREBASE_PROJECT_ID=
FIREBASE_CREDENTIALS_PATH=
GOOGLE_MAPS_API_KEY=
DEFAULT_TIMEZONE=Asia/Riyadh
SUPER_ADMIN_EMAIL=
SUPER_ADMIN_PASSWORD=
```

Never commit real secrets.

---

# Definition of done

A task is complete only when:

- Code is implemented.
- Formatting and lint pass.
- Relevant tests pass.
- Errors are handled.
- Arabic and English labels exist.
- Permissions are enforced.
- Tenant isolation is checked.
- Documentation is updated.
- No debug placeholders remain.

Maintain task status in `docs/IMPLEMENTATION_PLAN.md` as:

- Not started
- In progress
- Blocked
- Completed

---

# First action now

Perform these actions in order:

1. Inspect the repository and development environment.
2. Report the repository root, branch, existing files/apps, tool versions, missing tools, and disk-space risks.
3. Read all current documentation and configuration.
4. Create the required planning documents.
5. Produce a concise audit summary and final implementation plan.
6. List only real blockers.
7. After writing the plan, start Day 1 and Day 2 foundations unless a true blocker prevents safe work.

Do not generate random screens first.

Do not create separate mobile applications.

Do not wait for Figma.

Build the system according to this specification and maintain the 30-day execution plan.
