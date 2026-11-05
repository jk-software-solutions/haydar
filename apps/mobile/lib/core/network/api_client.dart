import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../storage/secure_storage.dart';

const apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  // Production is the safe default for installed APKs. Local development can
  // still override it with --dart-define=API_BASE_URL=...
  defaultValue: 'https://2-28-31-153.sslip.io/api/v1',
);

final dioProvider = Provider<Dio>((ref) {
  final storage = ref.watch(secureStorageProvider);
  final dio = Dio(
    BaseOptions(
      baseUrl: apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 20),
      headers: const <String, String>{'Accept': 'application/json'},
    ),
  );

  Future<void>? refreshInFlight;

  Future<void> refreshAccessToken() async {
    final refreshToken = await storage.read(key: 'refresh_token');
    if (refreshToken == null || refreshToken.isEmpty) {
      throw StateError('A refresh token is required.');
    }
    final refreshDio = Dio(BaseOptions(baseUrl: apiBaseUrl));
    try {
      final response = await refreshDio.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: <String, String>{'refresh_token': refreshToken},
      );
      final data = response.data ?? <String, dynamic>{};
      final accessToken = data['access_token'] as String?;
      final rotatedRefreshToken = data['refresh_token'] as String?;
      if (accessToken == null || rotatedRefreshToken == null) {
        throw StateError(
          'The server returned an incomplete refreshed session.',
        );
      }
      await storage.write(key: 'access_token', value: accessToken);
      await storage.write(key: 'refresh_token', value: rotatedRefreshToken);
    } finally {
      refreshDio.close(force: true);
    }
  }

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final path = options.path;
        if (!path.startsWith('/auth/')) {
          final accessToken = await storage.read(key: 'access_token');
          if (accessToken != null && accessToken.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $accessToken';
          }
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        final request = error.requestOptions;
        final path = request.path;
        final alreadyRetried = request.extra['authRetried'] == true;
        final isAuthRoute = path.startsWith('/auth/');
        if (error.response?.statusCode != 401 ||
            alreadyRetried ||
            isAuthRoute) {
          handler.next(error);
          return;
        }
        try {
          refreshInFlight ??= refreshAccessToken();
          await refreshInFlight;
          refreshInFlight = null;
          final accessToken = await storage.read(key: 'access_token');
          if (accessToken == null || accessToken.isEmpty) {
            handler.next(error);
            return;
          }
          final retryOptions = request.copyWith(
            headers: <String, dynamic>{
              ...request.headers,
              'Authorization': 'Bearer $accessToken',
            },
            extra: <String, dynamic>{...request.extra, 'authRetried': true},
          );
          final response = await dio.fetch<dynamic>(retryOptions);
          handler.resolve(response);
        } on Object {
          refreshInFlight = null;
          handler.next(error);
        }
      },
    ),
  );
  ref.onDispose(dio.close);
  return dio;
});
