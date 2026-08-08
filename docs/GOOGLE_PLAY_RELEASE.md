# Google Play release checklist

## Required external inputs

- Final production HTTPS API URL and verified TLS certificate.
- Play Console developer account and application record for `com.jawadsites.haydar`.
- Secure backup of `android/release/hadir-upload.jks` and `android/key.properties`.
- Final support email/website and privacy-policy public URL.
- Firebase `google-services.json` if push delivery is enabled.
- Restricted Google Maps Android key if an embedded map picker is enabled.

## Build

Generate an upload key once with `scripts/generate-android-upload-key.ps1`. Back up both ignored
files before publishing; losing the upload key complicates future updates. Build only with the real
endpoint:

```powershell
.\scripts\build-android-release.ps1 -ApiBaseUrl https://api.your-domain.tld/api/v1
```

The script rejects localhost and placeholder domains, runs clean dependency resolution, analysis,
tests, signed APK and AAB builds, and prints SHA-256 for both artifacts.

## Store listing

- App name: `HADIR | حاضر`
- Short description: `Secure attendance, tasks, leave, and workforce operations for your company.`
- Arabic short description: `حضور آمن ومهام وإجازات وعمليات موظفين لشركتك.`
- Category: Business
- Support and privacy links: replace with public HTTPS URLs before submission.
- Upload phone screenshots for Arabic and English employee/manager flows without real employee PII.
- Use the branded launcher source at `apps/mobile/assets/branding/hadir_launcher.png`.

## Policy and testing declarations

Declare precise location and camera use: location verifies branch attendance/presence; camera scans
branch QR codes. Biometrics never leave the device. Complete Data safety from the actual deployed
storage/retention configuration. Explain account access and company invitation flow to reviewers.

Run closed/internal testing first. Test fresh install, upgrade, Arabic RTL, English LTR, denied
location/camera, GPS inside/outside geofence, QR valid/expired/wrong branch, approved/replacement
device, check-in/out, requests, tasks, documents, and logout on at least one physical Android 16
device. Confirm the AAB in Play App Signing and retain the Play-generated certificate fingerprints.
