import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/storage/secure_storage.dart';

final authApiProvider = Provider<AuthApi>((ref) {
  return AuthApi(dio: ref.watch(dioProvider), ref: ref);
});

class AuthApi {
  AuthApi({required this.dio, required this.ref});

  static const _accessTokenKey = 'access_token';
  static const _refreshTokenKey = 'refresh_token';

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
    await _storeTokens(session);
    return session;
  }

  Future<void> requestPasswordReset({required String email}) async {
    await dio.post<void>(
      '/auth/password-reset/request',
      data: <String, String>{'email': email},
    );
  }

  Future<void> confirmPasswordReset({
    required String token,
    required String newPassword,
  }) async {
    await dio.post<void>(
      '/auth/password-reset/confirm',
      data: <String, String>{'token': token, 'new_password': newPassword},
    );
  }

  Future<AuthSession> activateInvitation({
    required String activationToken,
    required String password,
  }) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/auth/invitations/activate',
      data: <String, String>{
        'activation_token': activationToken,
        'password': password,
      },
    );
    final session = AuthSession.fromJson(response.data ?? <String, dynamic>{});
    await _storeTokens(session);
    return session;
  }

  Future<AuthSession?> restoreSession() async {
    final storage = ref.read(secureStorageProvider);
    final accessToken = await storage.read(key: _accessTokenKey);
    final refreshToken = await storage.read(key: _refreshTokenKey);
    if (accessToken == null || refreshToken == null) {
      return null;
    }

    try {
      final response = await dio.get<Map<String, dynamic>>(
        '/auth/session',
        options: Options(
          headers: <String, String>{'Authorization': 'Bearer $accessToken'},
        ),
      );
      return AuthSession.fromSessionJson(
        response.data ?? <String, dynamic>{},
        accessToken: accessToken,
        refreshToken: refreshToken,
      );
    } on DioException catch (error) {
      if (error.response?.statusCode != 401) {
        rethrow;
      }
      return refreshSession(refreshToken: refreshToken);
    }
  }

  Future<AuthSession> refreshSession({String? refreshToken}) async {
    final storage = ref.read(secureStorageProvider);
    final storedRefreshToken =
        refreshToken ?? await storage.read(key: _refreshTokenKey);
    if (storedRefreshToken == null) {
      throw StateError('A refresh token is required.');
    }
    try {
      final response = await dio.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: <String, String>{'refresh_token': storedRefreshToken},
      );
      final session = AuthSession.fromJson(
        response.data ?? <String, dynamic>{},
      );
      await _storeTokens(session);
      return session;
    } on DioException {
      await clearLocalSession();
      rethrow;
    }
  }

  Future<void> logout() async {
    final storage = ref.read(secureStorageProvider);
    final refreshToken = await storage.read(key: _refreshTokenKey);
    try {
      if (refreshToken != null) {
        await dio.post<void>(
          '/auth/logout',
          data: <String, String>{'refresh_token': refreshToken},
        );
      }
    } finally {
      await clearLocalSession();
    }
  }

  Future<void> clearLocalSession() async {
    final storage = ref.read(secureStorageProvider);
    await storage.delete(key: _accessTokenKey);
    await storage.delete(key: _refreshTokenKey);
  }

  Future<void> _storeTokens(AuthSession session) async {
    final storage = ref.read(secureStorageProvider);
    await storage.write(key: _accessTokenKey, value: session.accessToken);
    await storage.write(key: _refreshTokenKey, value: session.refreshToken);
  }
}

class AuthSession {
  const AuthSession({
    required this.accessToken,
    required this.refreshToken,
    required this.userId,
    required this.email,
    required this.companyId,
    required this.membershipId,
    required this.companyName,
    required this.fullName,
    required this.roles,
  });

  factory AuthSession.fromJson(Map<String, dynamic> json) {
    final session =
        json['session'] as Map<String, dynamic>? ?? <String, dynamic>{};
    return AuthSession.fromSessionJson(
      session,
      accessToken: json['access_token'] as String? ?? '',
      refreshToken: json['refresh_token'] as String? ?? '',
    );
  }

  factory AuthSession.fromSessionJson(
    Map<String, dynamic> session, {
    required String accessToken,
    required String refreshToken,
  }) {
    final user =
        session['user'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final company =
        session['company'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final roles = session['roles'] as List<dynamic>? ?? <dynamic>[];
    return AuthSession(
      accessToken: accessToken,
      refreshToken: refreshToken,
      userId: user['id'] as String? ?? '',
      email: user['email'] as String? ?? '',
      companyId: company['id'] as String? ?? '',
      membershipId: session['membership_id'] as String? ?? '',
      companyName: company['display_name'] as String? ?? '',
      fullName: user['full_name'] as String? ?? '',
      roles: roles.map((role) => '$role').toList(growable: false),
    );
  }

  final String accessToken;
  final String refreshToken;
  final String userId;
  final String email;
  final String companyId;
  final String membershipId;
  final String companyName;
  final String fullName;
  final List<String> roles;
}
