# DawamTech | دوام تك — Google Play release

## Release artifact

- Package: `com.jawadsites.haydar`
- Version: `1.0.1` (version code `2`)
- Upload file: `apps/mobile/build/app/outputs/bundle/release/app-release.aab`
- API endpoint compiled into this release: `https://2-28-31-153.sslip.io/api/v1`

The release is signed with the existing upload keystore configured by the
ignored local file `apps/mobile/android/key.properties`. Never commit that
file or the `.jks` file.

## Upload steps

1. Open Google Play Console and create/select the app with package
   `com.jawadsites.haydar`.
2. Complete the store listing, app category, content rating, privacy policy,
   Data safety form, and app access instructions.
3. Open **Testing** (recommended first) or **Production**, create a release,
   and upload `app-release.aab`.
4. Add release notes, review the warnings, and submit the release.

The APK is only for direct device testing; Google Play uses the AAB.
