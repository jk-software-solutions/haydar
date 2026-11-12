import 'dart:async';
import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/services.dart';

import '../../features/auth/application/auth_api.dart';
import '../../features/notifications/application/notification_api.dart';

/// Connects the Android device to the server-side FCM token registry.
///
/// All failures are deliberately best-effort: a missing Firebase setup must
/// not prevent an employee from signing in or recording attendance.
class PushNotificationService {
  PushNotificationService(this._notifications, {this.onNotification});

  static const MethodChannel _notificationChannel = MethodChannel(
    'hadir/notifications',
  );

  final NotificationApi _notifications;
  final void Function()? onNotification;
  bool _initialized = false;
  String? _registeredToken;
  String? _registeredMembershipId;
  DateTime? _lastRegistrationAttempt;
  AuthSession? _session;
  StreamSubscription<RemoteMessage>? _messageSubscription;
  StreamSubscription<String>? _tokenSubscription;

  Future<void> register(AuthSession session) async {
    if (!Platform.isAndroid) return;
    _session = session;
    if (_registeredMembershipId != session.membershipId) {
      _registeredMembershipId = session.membershipId;
      _registeredToken = null;
      _lastRegistrationAttempt = null;
    }
    if (_registeredToken != null) return;
    final now = DateTime.now();
    if (_lastRegistrationAttempt != null &&
        now.difference(_lastRegistrationAttempt!) < const Duration(minutes: 2)) {
      return;
    }
    _lastRegistrationAttempt = now;

    try {
      if (!_initialized) {
        await Firebase.initializeApp();
        _initialized = true;
        await FirebaseMessaging.instance.requestPermission(
          alert: true,
          badge: true,
          sound: true,
        );
        _messageSubscription = FirebaseMessaging.onMessage.listen((message) {
          final notification = message.notification;
          final title = notification?.title ?? message.data['title'] ?? 'HADIR';
          final body =
              notification?.body ?? message.data['body'] ?? 'لديك إشعار جديد';
          unawaited(_showNotification(title, body));
          onNotification?.call();
        });
        _tokenSubscription = FirebaseMessaging.instance.onTokenRefresh.listen((
          token,
        ) {
          final currentSession = _session;
          if (currentSession != null) {
            _register(currentSession, token);
          }
        });
      }

      final token = await FirebaseMessaging.instance.getToken();
      if (token != null && token.isNotEmpty &&
          _session?.membershipId == session.membershipId) {
        await _register(session, token);
      }
    } on Object catch (_) {
      // FCM is optional until the server Firebase service account is set.
    }
  }

  Future<void> _register(AuthSession session, String token) async {
    if (_registeredToken == token) return;
    try {
      await _notifications.registerPushToken(session, token);
      _registeredToken = token;
    } on Object catch (_) {
      // The authenticated workspace retries after the throttle interval.
    }
  }

  Future<void> _showNotification(String title, String body) async {
    try {
      await _notificationChannel.invokeMethod<void>('showNotification', {
        'title': title,
        'body': body,
      });
    } on Object {
      // Keep the ringtone fallback for devices where notification posting is
      // unavailable, while never interrupting the authenticated session.
      try {
        await _notificationChannel.invokeMethod<void>('playNotificationSound');
      } on Object {
        // Best effort only.
      }
    }
  }

  Future<void> playNotificationSound() async {
    try {
      await _notificationChannel.invokeMethod<void>('playNotificationSound');
    } on Object {
      // Best effort only; notification delivery must remain independent.
    }
  }

  Future<void> dispose() async {
    await _messageSubscription?.cancel();
    await _tokenSubscription?.cancel();
  }
}
