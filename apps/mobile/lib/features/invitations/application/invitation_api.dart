import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../auth/application/auth_controller.dart';

final invitationApiProvider = Provider<InvitationApi>((ref) {
  return InvitationApi(dio: ref.watch(dioProvider), ref: ref);
});

class InvitationApi {
  InvitationApi({required this.dio, required this.ref});

  final Dio dio;
  final Ref ref;

  Options get _authorization {
    final token = ref.read(authControllerProvider).session?.accessToken;
    if (token == null) {
      throw StateError('An authenticated session is required.');
    }
    return Options(headers: <String, String>{'Authorization': 'Bearer $token'});
  }

  Future<List<InvitationSummary>> list() async {
    final response = await dio.get<Map<String, dynamic>>(
      '/invitations',
      options: _authorization,
    );
    final items = response.data?['items'] as List<dynamic>? ?? <dynamic>[];
    return items
        .whereType<Map<String, dynamic>>()
        .map(InvitationSummary.fromJson)
        .toList(growable: false);
  }

  Future<CreatedInvitation> create({
    required String email,
    required String fullName,
    required String roleCode,
  }) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/invitations',
      options: _authorization,
      data: <String, String>{
        'email': email,
        'full_name': fullName,
        'role_code': roleCode,
      },
    );
    return CreatedInvitation.fromJson(response.data ?? <String, dynamic>{});
  }

  Future<CreatedInvitation> resendCode(String invitationId) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/invitations/$invitationId/resend-code',
      options: _authorization,
    );
    return CreatedInvitation.fromJson(response.data ?? <String, dynamic>{});
  }
}

class InvitationSummary {
  const InvitationSummary({
    required this.id,
    required this.email,
    required this.fullName,
    required this.roleCode,
    required this.status,
    required this.expiresAt,
  });

  factory InvitationSummary.fromJson(Map<String, dynamic> json) {
    return InvitationSummary(
      id: json['id'] as String? ?? '',
      email: json['email'] as String? ?? '',
      fullName: json['full_name'] as String? ?? '',
      roleCode: json['role_code'] as String? ?? '',
      status: json['status'] as String? ?? '',
      expiresAt: DateTime.tryParse(json['expires_at'] as String? ?? ''),
    );
  }

  final String id;
  final String email;
  final String fullName;
  final String roleCode;
  final String status;
  final DateTime? expiresAt;
}

class CreatedInvitation extends InvitationSummary {
  const CreatedInvitation({
    required super.id,
    required super.email,
    required super.fullName,
    required super.roleCode,
    required super.status,
    required super.expiresAt,
    required this.activationToken,
  });

  factory CreatedInvitation.fromJson(Map<String, dynamic> json) {
    final base = InvitationSummary.fromJson(json);
    return CreatedInvitation(
      id: base.id,
      email: base.email,
      fullName: base.fullName,
      roleCode: base.roleCode,
      status: base.status,
      expiresAt: base.expiresAt,
      activationToken: json['activation_token'] as String? ?? '',
    );
  }

  final String activationToken;
}
