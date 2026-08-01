import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/storage/secure_storage.dart';

final authApiProvider = Provider<AuthApi>((ref) {
  return AuthApi(
    dio: ref.watch(dioProvider),
    ref: ref,
  );
});

class AuthApi {
  AuthApi({required this.dio, required this.ref});

  final Dio dio;
  final Ref ref;

  Future<AuthSession> login({
    required String email,
    required String password,
  }) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/auth/login',
      data: <String, String>{'email': email, 'password': password},
    );
    final session = AuthSession.fromJson(response.data ?? <String, dynamic>{});
    final storage = ref.read(secureStorageProvider);
    await storage.write(key: 'access_token', value: session.accessToken);
    await storage.write(key: 'refresh_token', value: session.refreshToken);
    return session;
  }
}

class AuthSession {
  const AuthSession({
    required this.accessToken,
    required this.refreshToken,
    required this.companyName,
    required this.fullName,
    required this.roles,
  });

  factory AuthSession.fromJson(Map<String, dynamic> json) {
    final session = json['session'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final user = session['user'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final company = session['company'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final roles = session['roles'] as List<dynamic>? ?? <dynamic>[];
    return AuthSession(
      accessToken: json['access_token'] as String? ?? '',
      refreshToken: json['refresh_token'] as String? ?? '',
      companyName: company['display_name'] as String? ?? '',
      fullName: user['full_name'] as String? ?? '',
      roles: roles.map((role) => '$role').toList(growable: false),
    );
  }

  final String accessToken;
  final String refreshToken;
  final String companyName;
  final String fullName;
  final List<String> roles;
}
