import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

const apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000/api/v1',
);

final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 20),
      headers: const <String, String>{'Accept': 'application/json'},
    ),
  );
  ref.onDispose(dio.close);
  return dio;
});
