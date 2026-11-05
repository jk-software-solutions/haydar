import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/file_upload.dart';
import '../../auth/application/auth_api.dart';

final requestApiProvider = Provider<RequestApi>(
  (ref) => RequestApi(ref.watch(dioProvider)),
);

class RequestApi {
  RequestApi(this.dio);
  final Dio dio;
  Options _auth(AuthSession session, {bool idempotent = false}) => Options(
    headers: <String, String>{
      'Authorization': 'Bearer ${session.accessToken}',
      if (idempotent)
        'Idempotency-Key':
            'mobile-${DateTime.now().toUtc().microsecondsSinceEpoch}',
    },
  );

  Future<List<RequestItem>> permissions(
    AuthSession session, {
    bool allCompany = false,
  }) async => _items(
    session,
    allCompany ? '/permission-requests' : '/permission-requests?mine=true',
    kind: 'permission',
  );
  Future<List<RequestItem>> leaves(
    AuthSession session, {
    bool allCompany = false,
  }) async => _items(
    session,
    allCompany ? '/leave/requests' : '/leave/requests?mine=true',
    kind: 'leave',
  );

  Future<List<RequestItem>> _items(
    AuthSession session,
    String path, {
    required String kind,
  }) async {
    final response = await dio.get<List<dynamic>>(
      path,
      options: _auth(session),
    );
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map((item) => RequestItem.fromJson(item, kind: kind))
        .toList(growable: false);
  }

  Future<void> review(
    AuthSession session,
    RequestItem item,
    String decision,
  ) async {
    final path = item.kind == 'permission'
        ? '/permission-requests/${item.id}/review'
        : '/leave/requests/${item.id}/review';
    await dio.post<void>(
      path,
      options: _auth(session, idempotent: true),
      data: <String, String>{'decision': decision},
    );
  }

  Future<List<LeaveTypeItem>> leaveTypes(AuthSession session) async {
    final response = await dio.get<List<dynamic>>(
      '/leave/types',
      options: _auth(session),
    );
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(LeaveTypeItem.fromJson)
        .toList(growable: false);
  }

  Future<List<LeaveBalanceItem>> leaveBalances(AuthSession session) async {
    final response = await dio.get<List<dynamic>>(
      '/leave/balances',
      options: _auth(session),
    );
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(LeaveBalanceItem.fromJson)
        .toList(growable: false);
  }

  Future<void> createPermission(
    AuthSession session, {
    required String type,
    required DateTime startsAt,
    DateTime? endsAt,
    required String reason,
  }) async {
    await dio.post<void>(
      '/permission-requests',
      options: _auth(session),
      data: <String, dynamic>{
        'request_type': type,
        'starts_at': startsAt.toUtc().toIso8601String(),
        if (endsAt != null) 'ends_at': endsAt.toUtc().toIso8601String(),
        'reason': reason,
      },
    );
  }

  Future<void> createLeave(
    AuthSession session, {
    required String leaveTypeId,
    required DateTime startsOn,
    required DateTime endsOn,
    required String reason,
  }) async {
    String day(DateTime value) => value.toIso8601String().substring(0, 10);
    await dio.post<void>(
      '/leave/requests',
      options: _auth(session),
      data: <String, dynamic>{
        'leave_type_id': leaveTypeId,
        'starts_on': day(startsOn),
        'ends_on': day(endsOn),
        'reason': reason,
      },
    );
  }

  Future<String> upload(
    AuthSession session, {
    required String filename,
    required List<int> bytes,
  }) async {
    final form = FormData.fromMap(<String, dynamic>{
      'upload': MultipartFile.fromBytes(
        bytes,
        filename: filename,
        contentType: uploadMediaType(filename),
      ),
    });
    final response = await dio.post<Map<String, dynamic>>(
      '/files',
      options: _auth(session),
      data: form,
    );
    return response.data?['id'] as String? ?? '';
  }

  Future<void> createDocument(
    AuthSession session, {
    required String type,
    required String fileId,
    String? number,
    DateTime? expiresOn,
  }) async {
    await dio.post<void>(
      '/documents',
      options: _auth(session),
      data: <String, dynamic>{
        'document_type': type,
        'document_number': number,
        'expires_on': expiresOn?.toIso8601String().substring(0, 10),
        'attachment_file_id': fileId,
        'reminder_days': 30,
      },
    );
  }
}

class RequestItem {
  const RequestItem({
    required this.id,
    required this.kind,
    required this.employeeName,
    required this.employeeEmail,
    required this.type,
    required this.status,
    required this.reason,
    required this.from,
    required this.to,
  });
  factory RequestItem.fromJson(
    Map<String, dynamic> json, {
    required String kind,
  }) => RequestItem(
    id: json['id'] as String? ?? '',
    kind: kind,
    employeeName: json['employee_name'] as String? ?? '',
    employeeEmail: json['employee_email'] as String? ?? '',
    type:
        json['request_type'] as String? ??
        (json['leave_type_id'] as String? ?? 'leave'),
    status: json['status'] as String? ?? 'pending',
    reason: json['reason'] as String? ?? '',
    from: json['starts_at'] as String? ?? (json['starts_on'] as String? ?? ''),
    to: json['ends_at'] as String? ?? (json['ends_on'] as String? ?? ''),
  );
  final String id;
  final String kind;
  final String employeeName;
  final String employeeEmail;
  final String type;
  final String status;
  final String reason;
  final String from;
  final String to;
}

class LeaveTypeItem {
  const LeaveTypeItem({required this.id, required this.name});
  factory LeaveTypeItem.fromJson(Map<String, dynamic> json) => LeaveTypeItem(
    id: json['id'] as String? ?? '',
    name: json['name'] as String? ?? '',
  );
  final String id;
  final String name;
}

class LeaveBalanceItem {
  const LeaveBalanceItem({
    required this.leaveTypeId,
    required this.year,
    required this.allocatedDays,
    required this.usedDays,
    required this.remainingDays,
  });

  factory LeaveBalanceItem.fromJson(Map<String, dynamic> json) =>
      LeaveBalanceItem(
        leaveTypeId: json['leave_type_id'] as String? ?? '',
        year: json['year'] as int? ?? DateTime.now().year,
        allocatedDays: json['allocated_days'] as int? ?? 0,
        usedDays: json['used_days'] as int? ?? 0,
        remainingDays: json['remaining_days'] as int? ?? 0,
      );

  final String leaveTypeId;
  final int year;
  final int allocatedDays;
  final int usedDays;
  final int remainingDays;
}
