import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('native identifiers and visible product name stay stable', () {
    final androidBuild = File(
      'android/app/build.gradle.kts',
    ).readAsStringSync();
    final androidManifest = File(
      'android/app/src/main/AndroidManifest.xml',
    ).readAsStringSync();
    final iosProject = File(
      'ios/Runner.xcodeproj/project.pbxproj',
    ).readAsStringSync();
    final iosInfo = File('ios/Runner/Info.plist').readAsStringSync();

    expect(androidBuild, contains('namespace = "com.jawadsites.haydar"'));
    expect(androidBuild, contains('applicationId = "com.jawadsites.haydar"'));
    expect(androidManifest, contains('android:label="DawamTech | دوام تك"'));
    expect(
      iosProject,
      contains('PRODUCT_BUNDLE_IDENTIFIER = com.jawadsites.haydar;'),
    );
    expect(iosInfo, contains('<string>DawamTech | دوام تك</string>'));
  });
}
