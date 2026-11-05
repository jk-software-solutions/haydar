import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/device/installation_identity.dart';
import '../../../core/network/api_client.dart';
import '../../auth/application/auth_controller.dart';

final deviceApiProvider = Provider<DeviceApi>((ref) {
  return DeviceApi(dio: ref.watch(dioProvider), ref: ref);
});

final deviceBindingProvider = FutureProvider.autoDispose<DeviceBinding>((ref) {
  return ref.watch(deviceApiProvider).ensureCurrentInstallation();
});

class DeviceApi {
  DeviceApi({required this.dio, required this.ref});

  final Dio dio;
  final Ref ref;

  Options get _authorization {
    final token = ref.read(authControllerProvider).session?.accessToken;
    if (token == null) throw StateError('Authentication is required.');
    return Options(headers: <String, String>{'Authorization': 'Bearer $token'});
  }

  Future<DeviceBinding> ensureCurrentInstallation({String? reason}) async {
    final installationId = await ref
        .read(installationIdentityProvider)
        .getOrCreate();
    try {
      final response = await dio.post<Map<String, dynamic>>(
        '/devices/register',
        options: _authorization,
        data: <String, dynamic>{
          'installation_id': installationId,
          'platform': Platform.isIOS ? 'ios' : 'android',
          'device_name': Platform.isIOS ? 'iOS device' : 'Android device',
          'reason': ?reason,
        },
      );
      return DeviceBinding.fromJson(response.data ?? <String, dynamic>{});
    } on DioException catch (error) {
      final data = error.response?.data;
      if (data is Map<String, dynamic> &&
          data['code'] == 'device_change_reason_required') {
        return const DeviceBinding.needsReason();
      }
      rethrow;
    }
  }

  Future<List<DeviceChange>> listPendingChanges() async {
    final response = await dio.get<Map<String, dynamic>>(
      '/devices/change-requests',
      options: _authorization,
    );
    final items = response.data?['items'] as List<dynamic>? ?? <dynamic>[];
    return items
        .whereType<Map<String, dynamic>>()
        .map(DeviceChange.fromJson)
        .toList(growable: false);
  }

  Future<void> reviewChange(String id, {required bool approve}) async {
    await dio.post<void>(
      '/devices/change-requests/$id/${approve ? 'approve' : 'reject'}',
      options: _authorization,
      data: <String, String>{},
    );
  }
}

class DeviceBinding {
  const DeviceBinding({
    required this.status,
    required this.requiresApproval,
    this.changeRequestId,
  }) : needsChangeReason = false;

  const DeviceBinding.needsReason()
    : status = 'unregistered',
      requiresApproval = false,
      changeRequestId = null,
      needsChangeReason = true;

  factory DeviceBinding.fromJson(Map<String, dynamic> json) {
    final device =
        json['device'] as Map<String, dynamic>? ?? <String, dynamic>{};
    return DeviceBinding(
      status: device['status'] as String? ?? 'unknown',
      requiresApproval: json['requires_approval'] as bool? ?? false,
      changeRequestId: json['change_request_id'] as String?,
    );
  }

  final String status;
  final bool requiresApproval;
  final String? changeRequestId;
  final bool needsChangeReason;

  bool get isApproved => status == 'approved' && !requiresApproval;
}

class DeviceChange {
  const DeviceChange({
    required this.id,
    required this.reason,
    required this.status,
    required this.employeeName,
    required this.employeeEmail,
    required this.requestedDeviceName,
  });

  factory DeviceChange.fromJson(Map<String, dynamic> json) {
    return DeviceChange(
      id: json['id'] as String? ?? '',
      reason: json['reason'] as String? ?? '',
      status: json['status'] as String? ?? '',
      employeeName: json['employee_name'] as String? ?? '',
      employeeEmail: json['employee_email'] as String? ?? '',
      requestedDeviceName: json['requested_device_name'] as String? ?? '',
    );
  }

  final String id;
  final String reason;
  final String status;
  final String employeeName;
  final String employeeEmail;
  final String requestedDeviceName;
}
