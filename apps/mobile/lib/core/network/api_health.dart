import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

class ApiHealth {
  const ApiHealth({required this.isReady});

  const ApiHealth.ready() : isReady = true;

  final bool isReady;
}

final apiHealthProvider = FutureProvider<ApiHealth>((ref) async {
  final dio = ref.watch(dioProvider);
  final response = await dio.get<Map<String, dynamic>>('/health/ready');
  final status = response.data?['status'];
  if (status != 'ok') {
    throw StateError('API readiness returned $status');
  }
  return const ApiHealth.ready();
});
