import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../storage/secure_storage.dart';

String generateInstallationUuid([Random? random]) {
  final source = random ?? Random.secure();
  final bytes = List<int>.generate(16, (_) => source.nextInt(256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  String hex(int value) => value.toRadixString(16).padLeft(2, '0');
  return <String>[
    bytes.sublist(0, 4).map(hex).join(),
    bytes.sublist(4, 6).map(hex).join(),
    bytes.sublist(6, 8).map(hex).join(),
    bytes.sublist(8, 10).map(hex).join(),
    bytes.sublist(10).map(hex).join(),
  ].join('-');
}

final installationIdentityProvider = Provider<InstallationIdentity>((ref) {
  return InstallationIdentity(ref);
});

class InstallationIdentity {
  InstallationIdentity(this.ref);

  static const _storageKey = 'installation_uuid';
  final Ref ref;

  Future<String> getOrCreate() async {
    final storage = ref.read(secureStorageProvider);
    final existing = await storage.read(key: _storageKey);
    if (existing != null && existing.isNotEmpty) return existing;
    final value = generateInstallationUuid();
    await storage.write(key: _storageKey, value: value);
    return value;
  }
}
