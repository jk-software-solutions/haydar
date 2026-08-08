import 'package:flutter_test/flutter_test.dart';
import 'package:haydar/core/device/biometric_gate.dart';
import 'package:local_auth/local_auth.dart';

class FakeBiometricPlatform implements BiometricPlatform {
  bool supported = true;
  List<BiometricType> biometrics = <BiometricType>[BiometricType.fingerprint];
  bool authenticated = true;
  LocalAuthException? failure;
  int authenticationCalls = 0;

  @override
  Future<List<BiometricType>> availableBiometrics() async => biometrics;

  @override
  Future<bool> authenticate(String localizedReason) async {
    authenticationCalls += 1;
    if (failure case final error?) throw error;
    return authenticated;
  }

  @override
  Future<bool> isDeviceSupported() async => supported;
}

void main() {
  test('disabled policy skips all platform biometric calls', () async {
    final platform = FakeBiometricPlatform();
    final result = await BiometricGate(
      platform,
    ).confirm(policy: 'disabled', localizedReason: 'Confirm');

    expect(result, BiometricResult.skipped);
    expect(platform.authenticationCalls, 0);
  });

  test('reports unsupported and unenrolled capabilities separately', () async {
    final unsupported = FakeBiometricPlatform()..supported = false;
    expect(
      await BiometricGate(
        unsupported,
      ).confirm(policy: 'required', localizedReason: 'Confirm'),
      BiometricResult.unavailable,
    );

    final unenrolled = FakeBiometricPlatform()..biometrics = <BiometricType>[];
    expect(
      await BiometricGate(
        unenrolled,
      ).confirm(policy: 'required', localizedReason: 'Confirm'),
      BiometricResult.notEnrolled,
    );
  });

  test('distinguishes confirmation cancellation and lockout', () async {
    final confirmed = FakeBiometricPlatform();
    expect(
      await BiometricGate(
        confirmed,
      ).confirm(policy: 'optional', localizedReason: 'Confirm'),
      BiometricResult.confirmed,
    );

    final cancelled = FakeBiometricPlatform()..authenticated = false;
    expect(
      await BiometricGate(
        cancelled,
      ).confirm(policy: 'optional', localizedReason: 'Confirm'),
      BiometricResult.cancelled,
    );

    final locked = FakeBiometricPlatform()
      ..failure = const LocalAuthException(
        code: LocalAuthExceptionCode.temporaryLockout,
      );
    expect(
      await BiometricGate(
        locked,
      ).confirm(policy: 'required', localizedReason: 'Confirm'),
      BiometricResult.lockedOut,
    );
  });
}
