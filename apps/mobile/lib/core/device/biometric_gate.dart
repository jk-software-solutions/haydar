import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';

final biometricGateProvider = Provider<BiometricGate>(
  (ref) => BiometricGate(LocalBiometricPlatform()),
);

enum BiometricResult {
  confirmed,
  skipped,
  unavailable,
  notEnrolled,
  cancelled,
  lockedOut,
  failed,
}

abstract interface class BiometricPlatform {
  Future<bool> isDeviceSupported();
  Future<List<BiometricType>> availableBiometrics();
  Future<bool> authenticate(String localizedReason);
}

class LocalBiometricPlatform implements BiometricPlatform {
  LocalBiometricPlatform([LocalAuthentication? authentication])
    : _authentication = authentication ?? LocalAuthentication();

  final LocalAuthentication _authentication;

  @override
  Future<bool> isDeviceSupported() => _authentication.isDeviceSupported();

  @override
  Future<List<BiometricType>> availableBiometrics() =>
      _authentication.getAvailableBiometrics();

  @override
  Future<bool> authenticate(String localizedReason) =>
      _authentication.authenticate(
        localizedReason: localizedReason,
        biometricOnly: true,
        persistAcrossBackgrounding: true,
      );
}

class BiometricGate {
  const BiometricGate(this.platform);

  final BiometricPlatform platform;

  Future<BiometricResult> confirm({
    required String policy,
    required String localizedReason,
  }) async {
    if (policy == 'disabled') return BiometricResult.skipped;
    try {
      if (!await platform.isDeviceSupported()) {
        return BiometricResult.unavailable;
      }
      if ((await platform.availableBiometrics()).isEmpty) {
        return BiometricResult.notEnrolled;
      }
      return await platform.authenticate(localizedReason)
          ? BiometricResult.confirmed
          : BiometricResult.cancelled;
    } on LocalAuthException catch (error) {
      return switch (error.code) {
        LocalAuthExceptionCode.userCanceled ||
        LocalAuthExceptionCode.systemCanceled ||
        LocalAuthExceptionCode.userRequestedFallback =>
          BiometricResult.cancelled,
        LocalAuthExceptionCode.noBiometricsEnrolled ||
        LocalAuthExceptionCode.noCredentialsSet => BiometricResult.notEnrolled,
        LocalAuthExceptionCode.noBiometricHardware ||
        LocalAuthExceptionCode.biometricHardwareTemporarilyUnavailable =>
          BiometricResult.unavailable,
        LocalAuthExceptionCode.temporaryLockout ||
        LocalAuthExceptionCode.biometricLockout => BiometricResult.lockedOut,
        _ => BiometricResult.failed,
      };
    } on Object {
      return BiometricResult.failed;
    }
  }
}
