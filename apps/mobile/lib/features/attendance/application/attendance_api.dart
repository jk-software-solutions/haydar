import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/device/installation_identity.dart';
import '../../../core/network/api_client.dart';
import '../../auth/application/auth_api.dart';

final attendanceApiProvider = Provider<AttendanceApi>((ref) {
  return AttendanceApi(
    dio: ref.watch(dioProvider),
    installationIdentity: ref.watch(installationIdentityProvider),
  );
});

class AttendanceApi {
  AttendanceApi({required this.dio, required this.installationIdentity});

  final Dio dio;
  final InstallationIdentity installationIdentity;

  Options _auth(AuthSession session, {String? installationId}) => Options(
    headers: <String, String>{
      'Authorization': 'Bearer ${session.accessToken}',
      'X-Installation-ID': ?installationId,
    },
  );

  Future<List<AttendanceRecord>> list(
    AuthSession session, {
    bool allCompany = false,
  }) async {
    final response = await dio.get<List<dynamic>>(
      allCompany ? '/attendance' : '/attendance/me',
      options: _auth(session),
    );
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(AttendanceRecord.fromJson)
        .toList(growable: false);
  }

  Future<List<PresenceChallenge>> presenceChallenges(
    AuthSession session,
  ) async {
    final response = await dio.get<List<dynamic>>(
      '/presence-requests?mine=true',
      options: _auth(session),
    );
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(PresenceChallenge.fromJson)
        .toList(growable: false);
  }

  Future<void> respondToPresence({
    required AuthSession session,
    required String requestId,
    required double latitude,
    required double longitude,
  }) async {
    final installationId = await installationIdentity.getOrCreate();
    await dio.post<void>(
      '/presence-requests/$requestId/respond',
      data: <String, double>{'latitude': latitude, 'longitude': longitude},
      options: _auth(session, installationId: installationId),
    );
  }

  Future<AttendanceRecord> checkIn({
    required AuthSession session,
    required double latitude,
    required double longitude,
    required String method,
    required bool biometricConfirmed,
    String? qrToken,
  }) => _attendanceAction(
    path: '/attendance/check-in',
    session: session,
    latitude: latitude,
    longitude: longitude,
    method: method,
    biometricConfirmed: biometricConfirmed,
    qrToken: qrToken,
  );

  Future<AttendanceRecord> checkOut({
    required AuthSession session,
    required double latitude,
    required double longitude,
    required String method,
    required bool biometricConfirmed,
    String? qrToken,
  }) => _attendanceAction(
    path: '/attendance/check-out',
    session: session,
    latitude: latitude,
    longitude: longitude,
    method: method,
    biometricConfirmed: biometricConfirmed,
    qrToken: qrToken,
  );

  Future<AttendanceRecord> _attendanceAction({
    required String path,
    required AuthSession session,
    required double latitude,
    required double longitude,
    required String method,
    required bool biometricConfirmed,
    String? qrToken,
  }) async {
    final installationId = await installationIdentity.getOrCreate();
    final response = await dio.post<Map<String, dynamic>>(
      path,
      data: <String, dynamic>{
        'method': method,
        'latitude': latitude,
        'longitude': longitude,
        'biometric_confirmed': biometricConfirmed,
        'qr_token': ?qrToken,
      },
      options: _auth(session, installationId: installationId),
    );
    return AttendanceRecord.fromJson(response.data ?? <String, dynamic>{});
  }
}

class AttendanceRecord {
  const AttendanceRecord({
    required this.id,
    required this.workDate,
    required this.status,
    required this.checkedInAt,
    required this.checkedOutAt,
    required this.workedMinutes,
    required this.lateMinutes,
    required this.distanceLabel,
  });

  factory AttendanceRecord.fromJson(Map<String, dynamic> json) {
    return AttendanceRecord(
      id: json['id'] as String? ?? '',
      workDate: json['work_date'] as String? ?? '',
      status: json['status'] as String? ?? 'pending_review',
      checkedInAt: DateTime.tryParse(json['checked_in_at'] as String? ?? ''),
      checkedOutAt: DateTime.tryParse(json['checked_out_at'] as String? ?? ''),
      workedMinutes: json['worked_minutes'] as int? ?? 0,
      lateMinutes: json['late_minutes'] as int? ?? 0,
      distanceLabel: '',
    );
  }

  final String id;
  final String workDate;
  final String status;
  final DateTime? checkedInAt;
  final DateTime? checkedOutAt;
  final int workedMinutes;
  final int lateMinutes;
  final String distanceLabel;

  bool get isOpen => checkedInAt != null && checkedOutAt == null;
}

class PresenceChallenge {
  const PresenceChallenge({
    required this.requestId,
    required this.message,
    required this.deadlineAt,
    required this.status,
  });
  factory PresenceChallenge.fromJson(Map<String, dynamic> json) =>
      PresenceChallenge(
        requestId: json['request_id'] as String? ?? '',
        message: json['message'] as String? ?? '',
        deadlineAt: DateTime.tryParse(json['deadline_at'] as String? ?? ''),
        status: json['status'] as String? ?? 'pending',
      );
  final String requestId;
  final String message;
  final DateTime? deadlineAt;
  final String status;
  bool get canRespond =>
      status == 'pending' &&
      (deadlineAt?.isAfter(DateTime.now().toUtc()) ?? false);
}
