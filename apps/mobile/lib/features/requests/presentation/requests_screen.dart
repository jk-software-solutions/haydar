import 'dart:async';

import 'package:dio/dio.dart';
import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_api.dart';
import '../application/request_api.dart';

class RequestsScreen extends ConsumerStatefulWidget {
  const RequestsScreen({required this.session, super.key});
  final AuthSession session;
  @override
  ConsumerState<RequestsScreen> createState() => _RequestsScreenState();
}

class _RequestsScreenState extends ConsumerState<RequestsScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  List<RequestItem> _permissions = <RequestItem>[];
  List<RequestItem> _leaves = <RequestItem>[];
  List<LeaveTypeItem> _leaveTypes = <LeaveTypeItem>[];
  List<LeaveBalanceItem> _leaveBalances = <LeaveBalanceItem>[];
  Timer? _refreshTimer;
  bool _loading = true;
  String? _error;
  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _refresh();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 15),
      (_) => unawaited(_refresh()),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final api = ref.read(requestApiProvider);
      final values = await Future.wait<Object>(<Future<Object>>[
        api.permissions(widget.session),
        api.leaves(widget.session),
        api.leaveTypes(widget.session),
        api.leaveBalances(widget.session),
      ]);
      if (mounted) {
        setState(() {
          _permissions = values[0] as List<RequestItem>;
          _leaves = values[1] as List<RequestItem>;
          _leaveTypes = values[2] as List<LeaveTypeItem>;
          _leaveBalances = values[3] as List<LeaveBalanceItem>;
          _error = null;
        });
      }
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _message(Object error) {
    if (error is DioException && error.response?.data is Map<String, dynamic>) {
      final data = error.response!.data as Map<String, dynamic>;
      return switch (data['code']) {
        'invalid_session' =>
          _ar
              ? 'انتهت الجلسة. سجّل الدخول مرة أخرى.'
              : 'Your session expired. Sign in again.',
        'permission_denied' =>
          _ar
              ? 'ليست لديك صلاحية لهذا الطلب.'
              : 'You do not have permission for this request.',
        _ =>
          data['detail'] as String? ??
              (_ar ? 'تعذر تحميل الطلبات.' : 'Requests could not be loaded.'),
      };
    }
    return _ar
        ? 'تعذر الاتصال بالخادم. حاول مرة أخرى.'
        : 'Could not reach the server. Try again.';
  }

  Future<DateTime?> _date({bool withTime = false}) async {
    final now = DateTime.now();
    final date = await showDatePicker(
      context: context,
      firstDate: now.subtract(const Duration(days: 1)),
      lastDate: now.add(const Duration(days: 730)),
      initialDate: now,
    );
    if (date == null || !withTime || !mounted) return date;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.now(),
    );
    return time == null
        ? null
        : DateTime(date.year, date.month, date.day, time.hour, time.minute);
  }

  Future<void> _newPermission() async {
    final reason = TextEditingController();
    final starts = await _date(withTime: true);
    if (starts == null || !mounted) return;
    var type = 'multiple_hours';
    DateTime? ends = starts.add(const Duration(hours: 1));
    final submitted = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(_ar ? 'طلب استئذان' : 'Permission request'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                DropdownButtonFormField<String>(
                  initialValue: type,
                  decoration: InputDecoration(
                    labelText: _ar ? 'نوع الاستئذان' : 'Permission type',
                  ),
                  items: <DropdownMenuItem<String>>[
                    DropdownMenuItem<String>(
                      value: 'one_hour',
                      child: Text(_ar ? 'ساعة واحدة' : 'One hour'),
                    ),
                    DropdownMenuItem<String>(
                      value: 'multiple_hours',
                      child: Text(_ar ? 'فترة محددة' : 'Specific period'),
                    ),
                    DropdownMenuItem<String>(
                      value: 'until_shift_end',
                      child: Text(
                        _ar ? 'إلى نهاية الفترة/الوردية' : 'Until shift end',
                      ),
                    ),
                    DropdownMenuItem<String>(
                      value: 'custom',
                      child: Text(_ar ? 'مخصص' : 'Custom'),
                    ),
                  ],
                  onChanged: (value) => setDialogState(() {
                    type = value ?? type;
                    if (type == 'one_hour') {
                      ends = starts.add(const Duration(hours: 1));
                    }
                    if (type == 'until_shift_end') {
                      ends = null;
                    }
                  }),
                ),
                const SizedBox(height: 12),
                if (type != 'until_shift_end')
                  OutlinedButton.icon(
                    onPressed: () async {
                      final picked = await _date(withTime: true);
                      if (picked != null) {
                        setDialogState(() => ends = picked);
                      }
                    },
                    icon: const Icon(Icons.schedule_rounded),
                    label: Text(
                      ends == null
                          ? (_ar ? 'اختر وقت الرجوع' : 'Choose return time')
                          : '${_ar ? 'الرجوع' : 'Return'}: $ends',
                    ),
                  ),
                const SizedBox(height: 12),
                TextField(
                  controller: reason,
                  maxLines: 3,
                  decoration: InputDecoration(
                    labelText: _ar ? 'السبب' : 'Reason',
                    hintText: _ar
                        ? 'مثلاً: مراجعة مستوصف'
                        : 'Example: clinic visit',
                  ),
                ),
              ],
            ),
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(_ar ? 'إلغاء' : 'Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: Text(_ar ? 'إرسال' : 'Submit'),
            ),
          ],
        ),
      ),
    );
    if (submitted == true &&
        reason.text.trim().length >= 3 &&
        (type == 'until_shift_end' || ends != null)) {
      await ref
          .read(requestApiProvider)
          .createPermission(
            widget.session,
            type: type,
            startsAt: starts,
            endsAt: ends,
            reason: reason.text.trim(),
          );
      await _refresh();
    }
    reason.dispose();
  }

  Future<void> _extendPermission(RequestItem item) async {
    final currentEnd = DateTime.tryParse(item.to)?.toLocal();
    if (currentEnd == null) return;
    final selected = await _date(withTime: true);
    if (selected == null || !mounted) return;
    final end = selected;
    if (!end.isAfter(currentEnd)) {
      setState(
        () => _error = _ar
            ? 'اختر وقت رجوع بعد نهاية الإذن الحالي.'
            : 'Choose a return time after the current permission ends.',
      );
      return;
    }
    try {
      await ref
          .read(requestApiProvider)
          .createPermission(
            widget.session,
            type: 'custom',
            startsAt: currentEnd,
            endsAt: end,
            reason: _ar
                ? 'تمديد الإذن السابق: ${item.reason}'
                : 'Extension of previous permission: ${item.reason}',
          );
      await _refresh();
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    }
  }

  Future<void> _newLeave() async {
    if (_leaveTypes.isEmpty) {
      setState(
        () => _error = _ar
            ? 'لم يتم إعداد أنواع الإجازات.'
            : 'No leave types are configured.',
      );
      return;
    }
    final starts = await _date();
    if (starts == null || !mounted) return;
    final ends = await _date();
    if (ends == null || !mounted) return;
    final reason = TextEditingController();
    String typeId = _leaveTypes.first.id;
    final submitted = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(_ar ? 'طلب إجازة' : 'Leave request'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              DropdownButtonFormField<String>(
                initialValue: typeId,
                items: _leaveTypes
                    .map(
                      (type) => DropdownMenuItem<String>(
                        value: type.id,
                        child: Text(type.name),
                      ),
                    )
                    .toList(),
                onChanged: (value) =>
                    setDialogState(() => typeId = value ?? typeId),
              ),
              TextField(
                controller: reason,
                decoration: InputDecoration(
                  labelText: _ar ? 'السبب' : 'Reason',
                ),
              ),
            ],
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(_ar ? 'إلغاء' : 'Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: Text(_ar ? 'إرسال' : 'Submit'),
            ),
          ],
        ),
      ),
    );
    if (submitted == true && reason.text.trim().length >= 3) {
      await ref
          .read(requestApiProvider)
          .createLeave(
            widget.session,
            leaveTypeId: typeId,
            startsOn: starts,
            endsOn: ends,
            reason: reason.text.trim(),
          );
      await _refresh();
    }
    reason.dispose();
  }

  Future<void> _uploadDocument() async {
    try {
      const documentTypes = XTypeGroup(
        label: 'documents',
        extensions: <String>['pdf', 'jpg', 'jpeg', 'png', 'webp'],
      );
      final file = await openFile(
        acceptedTypeGroups: <XTypeGroup>[documentTypes],
      );
      if (file == null) return;
      final bytes = await file.readAsBytes();
      final fileId = await ref
          .read(requestApiProvider)
          .upload(widget.session, filename: file.name, bytes: bytes);
      await ref
          .read(requestApiProvider)
          .createDocument(widget.session, type: 'custom', fileId: fileId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              _ar
                  ? 'تم رفع الوثيقة للمراجعة.'
                  : 'Document uploaded for review.',
            ),
          ),
        );
      }
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    }
  }

  Widget _list(List<RequestItem> items) => RefreshIndicator(
    onRefresh: _refresh,
    child: ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        if (items.isEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Text(_ar ? 'لا توجد طلبات.' : 'No requests.'),
            ),
          ),
        ...items.map(
          (item) => Card(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(
                children: <Widget>[
                  ListTile(
                    title: Text(_requestTypeLabel(item.type)),
                    subtitle: Text(
                      '${_formatDateTime(item.from)} – ${_formatDateTime(item.to)}\n${item.reason}',
                    ),
                    isThreeLine: true,
                    trailing: Chip(label: Text(_statusLabel(item.status))),
                  ),
                  if (item.kind == 'permission' && item.status == 'approved')
                    Align(
                      alignment: AlignmentDirectional.centerEnd,
                      child: TextButton.icon(
                        onPressed: () => _extendPermission(item),
                        icon: const Icon(Icons.more_time_rounded),
                        label: Text(
                          _ar ? 'طلب تمديد الإذن' : 'Request extension',
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ],
    ),
  );

  String _leaveTypeName(String id) =>
      _leaveTypes
          .where((item) => item.id == id)
          .map((item) => item.name)
          .firstOrNull ??
      id;

  Widget _leaveList() => RefreshIndicator(
    onRefresh: _refresh,
    child: ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        Text(
          _ar ? 'أرصدة الإجازات' : 'Leave balances',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 8),
        if (_leaveBalances.isEmpty)
          Text(_ar ? 'لا توجد أرصدة مخصصة.' : 'No balances allocated.'),
        ..._leaveBalances.map(
          (balance) => Card(
            child: ListTile(
              title: Text(
                '${_leaveTypeName(balance.leaveTypeId)} · ${balance.year}',
              ),
              subtitle: Text(
                '${_ar ? 'الإجمالي' : 'Total'}: ${balance.allocatedDays} · '
                '${_ar ? 'المستخدم' : 'Used'}: ${balance.usedDays}',
              ),
              trailing: Chip(
                label: Text(
                  '${_ar ? 'المتبقي' : 'Remaining'} ${balance.remainingDays}',
                ),
              ),
            ),
          ),
        ),
        const Divider(height: 32),
        if (_leaves.isEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Text(_ar ? 'لا توجد طلبات.' : 'No requests.'),
            ),
          ),
        ..._leaves.map(
          (item) => Card(
            child: ListTile(
              title: Text(_requestTypeLabel(item.type)),
              subtitle: Text(
                '${_formatDateTime(item.from)} – ${_formatDateTime(item.to)}\n${item.reason}',
              ),
              isThreeLine: true,
              trailing: Chip(label: Text(_statusLabel(item.status))),
            ),
          ),
        ),
      ],
    ),
  );

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    return Column(
      children: <Widget>[
        if (_error != null)
          Material(
            color: Theme.of(context).colorScheme.errorContainer,
            child: ListTile(title: Text(_error!)),
          ),
        TabBar(
          controller: _tabs,
          tabs: <Widget>[
            Tab(text: _ar ? 'الاستئذان' : 'Permission'),
            Tab(text: _ar ? 'الإجازة' : 'Leave'),
            Tab(text: _ar ? 'الوثائق' : 'Documents'),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabs,
            children: <Widget>[
              _list(_permissions),
              _leaveList(),
              ListView(
                padding: const EdgeInsets.all(24),
                children: <Widget>[
                  Icon(
                    Icons.folder_copy_outlined,
                    size: 64,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    _ar
                        ? 'ارفع وثائقك بصيغة صورة أو PDF ليتم اعتمادها.'
                        : 'Upload an image or PDF for manager review.',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 20),
                  FilledButton.icon(
                    onPressed: _uploadDocument,
                    icon: const Icon(Icons.upload_file_rounded),
                    label: Text(_ar ? 'رفع وثيقة' : 'Upload document'),
                  ),
                ],
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: <Widget>[
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _newPermission,
                  icon: const Icon(Icons.schedule_send_rounded),
                  label: Text(_ar ? 'استئذان جديد' : 'New permission'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton.icon(
                  onPressed: _newLeave,
                  icon: const Icon(Icons.beach_access_outlined),
                  label: Text(_ar ? 'إجازة جديدة' : 'New leave'),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  String _requestTypeLabel(String type) => switch (type) {
    'one_hour' => _ar ? 'استئذان لمدة ساعة' : 'One-hour permission',
    'multiple_hours' =>
      _ar ? 'استئذان لفترة محددة' : 'Specific-period permission',
    'until_shift_end' =>
      _ar ? 'استئذان حتى نهاية الوردية' : 'Permission until shift end',
    'custom' => _ar ? 'استئذان مخصص' : 'Custom permission',
    _ => _ar ? 'طلب' : 'Request',
  };

  String _statusLabel(String status) => switch (status) {
    'pending' => _ar ? 'قيد الانتظار' : 'Pending',
    'approved' => _ar ? 'تمت الموافقة' : 'Approved',
    'rejected' => _ar ? 'مرفوض' : 'Rejected',
    'cancelled' => _ar ? 'ملغى' : 'Cancelled',
    _ => _ar ? 'قيد المراجعة' : 'Under review',
  };

  String _formatDateTime(String value) {
    final parsed = DateTime.tryParse(value);
    if (parsed == null) return value;
    final local = parsed.toLocal();
    final date = MaterialLocalizations.of(context).formatMediumDate(local);
    final time = MaterialLocalizations.of(
      context,
    ).formatTimeOfDay(TimeOfDay.fromDateTime(local));
    return '$date، $time';
  }
}
