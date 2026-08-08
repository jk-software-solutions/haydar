import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../auth/application/auth_api.dart';

final notificationApiProvider = Provider<NotificationApi>(
  (ref) => NotificationApi(ref.watch(dioProvider)),
);

class NotificationApi {
  NotificationApi(this.dio);
  final Dio dio;

  Options _auth(AuthSession session) => Options(
    headers: <String, String>{'Authorization': 'Bearer ${session.accessToken}'},
  );

  Future<List<AppNotification>> list(AuthSession session) async {
    final response = await dio.get<List<dynamic>>(
      '/notifications',
      options: _auth(session),
    );
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(AppNotification.fromJson)
        .toList(growable: false);
  }

  Future<int> unreadCount(AuthSession session) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/notifications/unread-count',
      options: _auth(session),
    );
    return response.data?['unread_count'] as int? ?? 0;
  }

  Future<void> markRead(AuthSession session, String id) =>
      dio.post<void>('/notifications/$id/read', options: _auth(session));

  Future<void> markAllRead(AuthSession session) =>
      dio.post<void>('/notifications/read-all', options: _auth(session));
}

class AppNotification {
  const AppNotification({
    required this.id,
    required this.kind,
    required this.title,
    required this.body,
    required this.deepLink,
    required this.urgent,
    required this.readAt,
    required this.createdAt,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) =>
      AppNotification(
        id: json['id'] as String? ?? '',
        kind: json['kind'] as String? ?? '',
        title: json['title'] as String? ?? '',
        body: json['body'] as String? ?? '',
        deepLink: json['deep_link'] as String? ?? '/app',
        urgent: json['urgent'] as bool? ?? false,
        readAt: DateTime.tryParse(json['read_at'] as String? ?? ''),
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
      );

  final String id;
  final String kind;
  final String title;
  final String body;
  final String deepLink;
  final bool urgent;
  final DateTime? readAt;
  final DateTime? createdAt;
}
