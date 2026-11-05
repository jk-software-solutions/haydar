import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/file_upload.dart';
import '../../auth/application/auth_api.dart';

final employeeProfileApiProvider = Provider<EmployeeProfileApi>(
  (ref) => EmployeeProfileApi(ref.watch(dioProvider)),
);

class EmployeeProfileApi {
  EmployeeProfileApi(this.dio);

  final Dio dio;

  Options _auth(AuthSession session) => Options(
    headers: <String, String>{'Authorization': 'Bearer ${session.accessToken}'},
  );

  Future<EmployeeProfileData> me(AuthSession session) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/employees/me',
      options: _auth(session),
    );
    return EmployeeProfileData.fromJson(response.data ?? <String, dynamic>{});
  }

  Future<List<EmployeeBranchAssignment>> myBranches(AuthSession session) async {
    final response = await dio.get<List<dynamic>>(
      '/branches/assignments/me',
      options: _auth(session),
    );
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(EmployeeBranchAssignment.fromJson)
        .toList(growable: false);
  }

  Future<List<EmployeeShiftAssignment>> myShifts(AuthSession session) async {
    final response = await dio.get<List<dynamic>>(
      '/shifts/assignments/me',
      options: _auth(session),
    );
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(EmployeeShiftAssignment.fromJson)
        .toList(growable: false);
  }

  Future<String> uploadImage(
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

  Future<EmployeeProfileData> setAvatar(
    AuthSession session, {
    required int version,
    required String? fileId,
  }) async {
    final response = await dio.patch<Map<String, dynamic>>(
      '/employees/me/avatar',
      options: _auth(session),
      data: <String, dynamic>{'version': version, 'avatar_file_id': fileId},
    );
    return EmployeeProfileData.fromJson(response.data ?? <String, dynamic>{});
  }
}

class EmployeeProfileData {
  const EmployeeProfileData({
    required this.displayName,
    required this.employeeNumber,
    required this.jobTitle,
    required this.avatarFileId,
    required this.version,
  });

  factory EmployeeProfileData.fromJson(Map<String, dynamic> json) =>
      EmployeeProfileData(
        displayName: json['display_name'] as String? ?? '',
        employeeNumber: json['employee_number'] as String?,
        jobTitle: json['job_title'] as String?,
        avatarFileId: json['avatar_file_id'] as String?,
        version: json['version'] as int? ?? 1,
      );

  final String displayName;
  final String? employeeNumber;
  final String? jobTitle;
  final String? avatarFileId;
  final int version;
}

class EmployeeBranchAssignment {
  const EmployeeBranchAssignment({
    required this.name,
    required this.code,
    required this.effectiveFrom,
    required this.effectiveTo,
  });

  factory EmployeeBranchAssignment.fromJson(Map<String, dynamic> json) =>
      EmployeeBranchAssignment(
        name: json['branch_name'] as String? ?? '',
        code: json['branch_code'] as String? ?? '',
        effectiveFrom: DateTime.tryParse(
          json['effective_from'] as String? ?? '',
        ),
        effectiveTo: DateTime.tryParse(json['effective_to'] as String? ?? ''),
      );

  final String name;
  final String code;
  final DateTime? effectiveFrom;
  final DateTime? effectiveTo;
}

class EmployeeShiftAssignment {
  const EmployeeShiftAssignment({
    required this.name,
    required this.code,
    required this.startTime,
    required this.endTime,
    required this.effectiveFrom,
    required this.effectiveTo,
  });

  factory EmployeeShiftAssignment.fromJson(Map<String, dynamic> json) =>
      EmployeeShiftAssignment(
        name: json['shift_name'] as String? ?? '',
        code: json['shift_code'] as String? ?? '',
        startTime: json['start_time'] as String? ?? '',
        endTime: json['end_time'] as String? ?? '',
        effectiveFrom: DateTime.tryParse(
          json['effective_from'] as String? ?? '',
        ),
        effectiveTo: DateTime.tryParse(json['effective_to'] as String? ?? ''),
      );

  final String name;
  final String code;
  final String startTime;
  final String endTime;
  final DateTime? effectiveFrom;
  final DateTime? effectiveTo;
}
