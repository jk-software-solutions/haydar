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

  Future<void> registerPushToken(
    AuthSession session,
    String token, {
    String? appVersion,
  }) async {
    await dio.post<Map<String, dynamic>>(
      '/notifications/push-tokens',
      options: _auth(session),
      data: <String, dynamic>{
        'token': token,
        'platform': 'android',
        if (appVersion != null && appVersion.isNotEmpty)
          'app_version': appVersion,
      },
    );
  }

  Future<NotificationPreferences> preferences(AuthSession session) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/notifications/preferences',
      options: _auth(session),
    );
    return NotificationPreferences.fromJson(
      response.data ?? <String, dynamic>{},
    );
  }

  Future<NotificationPreferences> updatePreferences(
    AuthSession session,
    NotificationPreferences preferences,
  ) async {
    final response = await dio.put<Map<String, dynamic>>(
      '/notifications/preferences',
      options: _auth(session),
      data: preferences.toJson(),
    );
    return NotificationPreferences.fromJson(
      response.data ?? <String, dynamic>{},
    );
  }
}

class NotificationPreferences {
  const NotificationPreferences({
    required this.inAppEnabled,
    required this.pushEnabled,
    required this.emailEnabled,
    required this.mutedKinds,
    required this.quietHoursStart,
    required this.quietHoursEnd,
  });

  factory NotificationPreferences.fromJson(Map<String, dynamic> json) =>
      NotificationPreferences(
        inAppEnabled: json['in_app_enabled'] as bool? ?? true,
        pushEnabled: json['push_enabled'] as bool? ?? true,
        emailEnabled: json['email_enabled'] as bool? ?? false,
        mutedKinds: (json['muted_kinds'] as List<dynamic>? ?? <dynamic>[])
            .map((value) => '$value')
            .toList(growable: false),
        quietHoursStart: json['quiet_hours_start'] as String?,
        quietHoursEnd: json['quiet_hours_end'] as String?,
      );

  final bool inAppEnabled;
  final bool pushEnabled;
  final bool emailEnabled;
  final List<String> mutedKinds;
  final String? quietHoursStart;
  final String? quietHoursEnd;

  Map<String, dynamic> toJson() => <String, dynamic>{
    'in_app_enabled': inAppEnabled,
    'push_enabled': pushEnabled,
    'email_enabled': emailEnabled,
    'muted_kinds': mutedKinds,
    'quiet_hours_start': quietHoursStart,
    'quiet_hours_end': quietHoursEnd,
  };
}

class AppNotification {
  const AppNotification({
    required this.id,
    required this.kind,
    required this.title,
    required this.body,
    required this.actorName,
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
        actorName: json['actor_name'] as String?,
        deepLink: json['deep_link'] as String? ?? '/app',
        urgent: json['urgent'] as bool? ?? false,
        readAt: DateTime.tryParse(json['read_at'] as String? ?? ''),
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
      );

  final String id;
  final String kind;
  final String title;
  final String body;
  final String? actorName;
  final String deepLink;
  final bool urgent;
  final DateTime? readAt;
  final DateTime? createdAt;
}
