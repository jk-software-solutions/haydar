import 'dart:async';

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
  NotificationPreferences? _preferences;
  bool _loading = true;
  String? _error;
  Timer? _refreshTimer;
  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _refresh();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 15),
      (_) => unawaited(_refresh()),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final items = await ref
          .read(notificationApiProvider)
          .list(widget.session);
      final preferences = await ref
          .read(notificationApiProvider)
          .preferences(widget.session);
      if (mounted) {
        setState(() {
          _items = items;
          _preferences = preferences;
        });
      }
    } on DioException catch (error) {
      if (mounted) {
        final detail = error.response?.data is Map<String, dynamic>
            ? (error.response!.data as Map<String, dynamic>)['detail']
            : null;
        setState(
          () => _error = detail is String && detail.isNotEmpty
              ? detail
              : (_ar
                    ? 'تعذر تحميل الإشعارات. تحقق من الاتصال ثم أعد المحاولة.'
                    : 'Notifications could not be loaded. Check your connection and try again.'),
        );
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

  Future<void> _editPreferences() async {
    final current = _preferences;
    if (current == null) return;
    var inApp = current.inAppEnabled;
    var push = current.pushEnabled;
    var email = current.emailEnabled;
    final mutedController = TextEditingController(
      text: current.mutedKinds.join(', '),
    );
    final startController = TextEditingController(
      text: current.quietHoursStart ?? '',
    );
    final endController = TextEditingController(
      text: current.quietHoursEnd ?? '',
    );
    final updated = await showDialog<NotificationPreferences>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(_ar ? 'تفضيلات الإشعارات' : 'Notification preferences'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                SwitchListTile(
                  value: inApp,
                  onChanged: (value) => setDialogState(() => inApp = value),
                  title: Text(_ar ? 'داخل التطبيق' : 'In-app notifications'),
                ),
                SwitchListTile(
                  value: push,
                  onChanged: (value) => setDialogState(() => push = value),
                  title: Text(_ar ? 'الإشعارات الفورية' : 'Push notifications'),
                ),
                SwitchListTile(
                  value: email,
                  onChanged: (value) => setDialogState(() => email = value),
                  title: Text(
                    _ar ? 'البريد الإلكتروني' : 'Email notifications',
                  ),
                ),
                TextField(
                  controller: mutedController,
                  decoration: InputDecoration(
                    labelText: _ar
                        ? 'أنواع مكتومة، مفصولة بفاصلة'
                        : 'Muted kinds, comma-separated',
                  ),
                ),
                TextField(
                  controller: startController,
                  decoration: InputDecoration(
                    labelText: _ar ? 'بداية الهدوء HH:MM' : 'Quiet start HH:MM',
                  ),
                ),
                TextField(
                  controller: endController,
                  decoration: InputDecoration(
                    labelText: _ar ? 'نهاية الهدوء HH:MM' : 'Quiet end HH:MM',
                  ),
                ),
              ],
            ),
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(_ar ? 'إلغاء' : 'Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(
                context,
                NotificationPreferences(
                  inAppEnabled: inApp,
                  pushEnabled: push,
                  emailEnabled: email,
                  mutedKinds: mutedController.text
                      .split(',')
                      .map((value) => value.trim())
                      .where((value) => value.isNotEmpty)
                      .toList(growable: false),
                  quietHoursStart: startController.text.trim().isEmpty
                      ? null
                      : startController.text.trim(),
                  quietHoursEnd: endController.text.trim().isEmpty
                      ? null
                      : endController.text.trim(),
                ),
              ),
              child: Text(_ar ? 'حفظ' : 'Save'),
            ),
          ],
        ),
      ),
    );
    mutedController.dispose();
    startController.dispose();
    endController.dispose();
    if (updated == null) return;
    try {
      final saved = await ref
          .read(notificationApiProvider)
          .updatePreferences(widget.session, updated);
      if (mounted) setState(() => _preferences = saved);
    } on Object catch (error) {
      if (mounted) setState(() => _error = '$error');
    }
  }

  String _notificationTitle(AppNotification item) {
    if (!_ar) return item.title;
    return switch (item.kind) {
      'permission_requested' => 'طلب استئذان جديد',
      'permission_approved' => 'تم اعتماد طلب الاستئذان',
      'permission_rejected' => 'تم رفض طلب الاستئذان',
      'leave_requested' => 'طلب إجازة جديد',
      'leave_reviewed' => 'تمت مراجعة طلب الإجازة',
      'geofence_exit_unauthorized' => 'مغادرة غير مصرح بها من النطاق',
      'task_created' => 'مهمة جديدة: ${item.title}',
      'task_comment_added' => 'رسالة جديدة على المهمة: ${item.title}',
      'task_status_changed' => 'تحديث حالة المهمة: ${item.title}',
      'task_completed' => 'اكتملت المهمة مع مرفق: ${item.title}',
      'device_change_requested' => 'طلب تغيير جهاز جديد',
      'missing_checkout' => 'تم إغلاق الوردية دون تسجيل الانصراف',
      'attendance_reminder' => 'تذكير بإثبات الحضور',
      'attendance_absent' => 'تم تسجيل الغياب',
      _ => 'إشعار جديد',
    };
  }

  String _notificationBody(AppNotification item) {
    final body = !_ar
        ? item.body
        : switch (item.kind) {
            'permission_requested' =>
              'أرسل أحد الموظفين طلب استئذان أو خروج مبكر للمراجعة.',
            'permission_approved' => 'تمت الموافقة على طلب الاستئذان.',
            'permission_rejected' => 'تم رفض طلب الاستئذان.',
            'leave_requested' => 'أرسل أحد الموظفين طلب إجازة للمراجعة.',
            'leave_reviewed' => 'تم تحديث حالة طلب الإجازة.',
            'geofence_exit_unauthorized' =>
              'بقي موظف خارج نطاق الفرع دون استئذان معتمد.',
            'task_created' => 'تم إسناد مهمة جديدة إليك.',
            'task_comment_added' =>
              'أضاف أحد المشاركين رسالة جديدة إلى المهمة.',
            'task_status_changed' => 'تم تحديث حالة المهمة.',
            'task_completed' =>
              'أنجز الموظف المهمة وأرفق الإيصال. افتح الإشعار لمراجعته.',
            'task_extension_approved' => 'تمت الموافقة على طلب تمديد المهمة.',
            'task_extension_rejected' => 'تم رفض طلب تمديد المهمة.',
            'device_change_requested' => 'طلب موظف اعتماد هاتف بديل للمراجعة.',
            'missing_checkout' =>
              'انتهت الوردية ومهلة الانصراف 30 دقيقة دون تسجيل خروج، فأُغلقت تلقائياً ويمكنك بدء وردية لاحقة.',
            'attendance_reminder' =>
              'لم تثبت حضورك بعد انتهاء فترة السماح. سجّل الحضور الآن أو أرسل طلب استئذان.',
            'attendance_absent' =>
              'انتهت الوردية دون تسجيل حضور، لذلك أُغلق اليوم كسجل غياب.',
            _ => 'لديك إشعار جديد. افتحه لمعرفة التفاصيل.',
          };
    final actor = item.actorName?.trim();
    if (actor == null || actor.isEmpty) return body;
    return '$body\n${_ar ? 'المنفّذ' : 'Actor'}: $actor';
  }

  String _formatDateTime(DateTime? raw) {
    if (raw == null) return '';
    final value = raw.toLocal();
    final date = MaterialLocalizations.of(context).formatMediumDate(value);
    final time = MaterialLocalizations.of(context).formatTimeOfDay(
      TimeOfDay.fromDateTime(value),
      alwaysUse24HourFormat: !_ar,
    );
    return '$date · $time';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_ar ? 'الإشعارات' : 'Notifications'),
        actions: <Widget>[
          IconButton(
            onPressed: _preferences == null ? null : _editPreferences,
            tooltip: _ar ? 'التفضيلات' : 'Preferences',
            icon: const Icon(Icons.tune_rounded),
          ),
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
                        title: Text(_notificationTitle(item)),
                        subtitle: Text(
                          '${_notificationBody(item)}\n${_formatDateTime(item.createdAt)}',
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
