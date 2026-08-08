import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_api.dart';
import '../application/notification_api.dart';

class NotificationScreen extends ConsumerStatefulWidget {
  const NotificationScreen({
    required this.session,
    required this.onOpenDeepLink,
    super.key,
  });

  final AuthSession session;
  final ValueChanged<String> onOpenDeepLink;

  @override
  ConsumerState<NotificationScreen> createState() => _NotificationScreenState();
}

class _NotificationScreenState extends ConsumerState<NotificationScreen> {
  List<AppNotification> _items = <AppNotification>[];
  bool _loading = true;
  String? _error;
  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    try {
      final items = await ref
          .read(notificationApiProvider)
          .list(widget.session);
      if (mounted) {
        setState(() => _items = items);
      }
    } on DioException catch (error) {
      if (mounted) {
        setState(() => _error = '${error.response?.data ?? error.message}');
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _open(AppNotification item) async {
    if (item.readAt == null) {
      await ref.read(notificationApiProvider).markRead(widget.session, item.id);
    }
    if (!mounted) return;
    Navigator.of(context).pop();
    widget.onOpenDeepLink(item.deepLink);
  }

  Future<void> _readAll() async {
    await ref.read(notificationApiProvider).markAllRead(widget.session);
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_ar ? 'الإشعارات' : 'Notifications'),
        actions: <Widget>[
          TextButton(
            onPressed: _items.any((item) => item.readAt == null)
                ? _readAll
                : null,
            child: Text(_ar ? 'قراءة الكل' : 'Read all'),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: <Widget>[
                  if (_error != null)
                    Card(
                      color: Theme.of(context).colorScheme.errorContainer,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Text(_error!),
                      ),
                    ),
                  if (_items.isEmpty)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(
                          _ar
                              ? 'لا توجد إشعارات بعد.'
                              : 'No notifications yet.',
                        ),
                      ),
                    ),
                  ..._items.map(
                    (item) => Card(
                      color: item.readAt == null
                          ? Theme.of(context).colorScheme.primaryContainer
                          : null,
                      child: ListTile(
                        leading: Icon(
                          item.urgent
                              ? Icons.priority_high_rounded
                              : Icons.notifications_outlined,
                        ),
                        title: Text(item.title),
                        subtitle: Text(
                          '${item.body}\n${item.createdAt?.toLocal() ?? ''}',
                        ),
                        isThreeLine: true,
                        onTap: () => _open(item),
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
