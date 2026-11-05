import 'package:flutter/services.dart';

class WifiSnapshot {
  const WifiSnapshot({required this.ssid, required this.bssid, this.level});

  final String ssid;
  final String bssid;
  final int? level;
}

class WifiInfo {
  static const MethodChannel _channel = MethodChannel('hadir/wifi');

  static Future<WifiSnapshot?> current() async {
    final accessGranted =
        await _channel.invokeMethod<bool>('requestAccess') ?? false;
    if (!accessGranted) return null;
    final value = await _channel.invokeMethod<Map<Object?, Object?>>(
      'currentConnection',
    );
    if (value == null) return null;
    final ssid = value['ssid'] as String?;
    final bssid = value['bssid'] as String?;
    if (ssid == null || bssid == null || ssid.isEmpty || bssid.isEmpty) {
      return null;
    }
    return WifiSnapshot(ssid: ssid, bssid: bssid.toLowerCase());
  }

  static Future<List<WifiSnapshot>> scanNetworks() async {
    final accessGranted =
        await _channel.invokeMethod<bool>('requestAccess') ?? false;
    if (!accessGranted) return const <WifiSnapshot>[];
    final values = await _channel.invokeMethod<List<dynamic>>('scanNetworks');
    return (values ?? const <dynamic>[])
        .whereType<Map<dynamic, dynamic>>()
        .map((value) {
          final ssid = value['ssid'] as String? ?? '';
          final bssid = value['bssid'] as String? ?? '';
          final level = value['level'] is int ? value['level'] as int : null;
          return WifiSnapshot(
            ssid: ssid,
            bssid: bssid.toLowerCase(),
            level: level,
          );
        })
        .where((item) => item.ssid.isNotEmpty && item.bssid.isNotEmpty)
        .toList(growable: false);
  }
}
