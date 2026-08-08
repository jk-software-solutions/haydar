import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../auth/application/auth_api.dart';

final teamApiProvider = Provider<TeamApi>(
  (ref) => TeamApi(ref.watch(dioProvider)),
);

class TeamApi {
  TeamApi(this.dio);
  final Dio dio;

  Future<List<TeamMember>> list(AuthSession session) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/employees?page_size=100',
      options: Options(
        headers: <String, String>{
          'Authorization': 'Bearer ${session.accessToken}',
        },
      ),
    );
    final items = response.data?['items'] as List<dynamic>? ?? <dynamic>[];
    return items
        .whereType<Map<String, dynamic>>()
        .map(TeamMember.fromJson)
        .toList(growable: false);
  }
}

class TeamMember {
  const TeamMember({
    required this.membershipId,
    required this.name,
    required this.email,
    required this.role,
    required this.status,
    required this.jobTitle,
    required this.attendanceEnabled,
  });

  factory TeamMember.fromJson(Map<String, dynamic> json) => TeamMember(
    membershipId: json['membership_id'] as String? ?? '',
    name: json['display_name'] as String? ?? '',
    email: json['email'] as String? ?? '',
    role: json['role_code'] as String? ?? '',
    status: json['membership_status'] as String? ?? '',
    jobTitle: json['job_title'] as String?,
    attendanceEnabled: json['attendance_enabled'] as bool? ?? false,
  );

  final String membershipId;
  final String name;
  final String email;
  final String role;
  final String status;
  final String? jobTitle;
  final bool attendanceEnabled;
}
