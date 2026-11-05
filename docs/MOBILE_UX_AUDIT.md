# HADIR mobile UX audit — 2026-08-26

This is a focused audit for the current polish pass. Existing API contracts and
server-side authorization remain authoritative.

| Screen / journey | User goal | Current issue | Severity | Change / status | Risk and test |
|---|---|---|---|---|---|
| Attendance | Record arrival or departure | GPS and QR were the only visible methods | HIGH | Added configured Wi‑Fi attendance with clear Arabic/English action | Requires real Android Wi‑Fi permission and an authorized branch BSSID |
| Attendance | Understand location review | Raw status, UUID and sample count were shown first | HIGH | Human-readable status, date/time and distance are primary; diagnostics are expandable | `flutter analyze`, widget smoke test, real manager review |
| Attendance / GPS map | Let an owner verify where an employee checked in or out | The record had no usable location view | HIGH | Each history row now opens a clean map with employee GPS points, branch marker, geofence circle, event time and distance | Requires API deployment and real manager GPS record |
| Attendance | Understand current state | Checkout state and errors need clear actions | HIGH | Existing check-in/check-out hierarchy retained; friendly Wi‑Fi errors added | Verify on a real device with active/inactive branch |
| Login | Sign in without uncertainty | The screen lacked a strong product identity and password visibility control | HIGH | Added HADIR brand treatment, show/hide password, and safer friendly error mapping | Verify Arabic/English keyboard and invalid-login states |
| Role dashboard | Decide what to do next | The first screen read like session/debug information | HIGH | Added role-aware greeting card, company/role context, quick actions, and collapsed technical session details | Verify each role and permission set |
| Team | Find an employee quickly | Employees were an unfiltered technical list | MEDIUM | Added search, initials, readable role/status labels, and purposeful empty states | Verify 360dp layout and inactive members |
| Requests | Understand request status and dates | Raw enum values and ISO timestamps were displayed | HIGH | Added localized request type/status labels and readable date/time formatting | Verify Arabic permission and leave flows |
| Tasks | Update a task | Status changes need immediate feedback | HIGH | Existing status colors, labels and refresh behavior retained | Verify employee update and manager refresh |
| Tasks / conversations | Send a useful update | File uploads could be rejected when Android supplied no MIME type; dates were technical strings | HIGH | Common documents and audio now send with an explicit API-supported type; message dates are localized | Verify image, PDF and audio attachments on a real device |
| Requests / notifications | Review approvals | Arabic sender/status clarity is important | MEDIUM | Existing localized response fields are used; continue audit of remaining raw enums | Verify Arabic device and owner flows |
| Invitations | Reuse an invitation later | Role, status and expiry were shown as raw codes | MEDIUM | Role/status/expiry are now human-readable in both languages; resend remains available | Verify resend and copy flow |
| Team / admin | Manage employees | Dense administration is better kept behind role permissions | MEDIUM | Existing role-aware navigation preserved | Verify each role's accessible destinations |
| Global theme | The client should see a calm business product | The previous system theme could open the dark admin-style palette on a dark device | HIGH | Centralized Material 3 tokens now use the light SaaS palette by default; dark theme remains defined and available for a future selector | Verify Arabic RTL at 360dp, 390dp and 412dp on a real device |

## Wi‑Fi attendance contract

An administrator enters one or more lines in the branch form using:

`SSID|BSSID`

The employee connects to that network and taps **تسجيل حضور عبر Wi‑Fi** or
**تسجيل انصراف عبر Wi‑Fi**. The Android client reads the current SSID/BSSID;
the API authorizes the pair against the selected branch. GPS coordinates are
not used for this method, while the existing GPS and QR methods are unchanged.

## Remaining real-device checks

- Grant nearby-device/Wi‑Fi access where Android requests it.
- Configure a real branch BSSID and test an authorized and unauthorized network.
- Confirm Wi‑Fi check-in, checkout, duplicate-session and inactive-subscription errors.
- Confirm Arabic and English labels at 360dp, 390dp and 412dp widths.
- Confirm the light palette on a device configured for dark system appearance; the app should remain light by default.
- Open the map icon on a GPS attendance record and verify the employee marker,
  branch marker, radius circle, check-in/check-out popups and distance.

## Blocked / not claimed

- Push notification sound still depends on Firebase credentials and mobile
  Firebase integration; no fake delivery is claimed.
- Full visual comparison against the two reference recordings requires a real
  Android device and is not proven by static analysis alone.
- The map uses Leaflet/OpenStreetMap tiles inside the existing WebView, so the
  map requires an internet connection when it is opened.
