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
  bool _loading = true;
  String? _error;
  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _refresh();
  }

  @override
  void dispose() {
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
      ]);
      if (mounted) {
        setState(() {
          _permissions = values[0] as List<RequestItem>;
          _leaves = values[1] as List<RequestItem>;
          _leaveTypes = values[2] as List<LeaveTypeItem>;
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
      return ((error.response!.data as Map<String, dynamic>)['detail']
              as String?) ??
          '$error';
    }
    return '$error';
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
    final ends = await _date(withTime: true);
    if (ends == null || !mounted) return;
    final submitted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(_ar ? 'طلب استئذان' : 'Permission request'),
        content: TextField(
          controller: reason,
          decoration: InputDecoration(labelText: _ar ? 'السبب' : 'Reason'),
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
    );
    if (submitted == true && reason.text.trim().length >= 3) {
      await ref
          .read(requestApiProvider)
          .createPermission(
            widget.session,
            type: 'custom',
            startsAt: starts,
            endsAt: ends,
            reason: reason.text.trim(),
          );
      await _refresh();
    }
    reason.dispose();
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
            child: ListTile(
              title: Text(item.type),
              subtitle: Text('${item.from} – ${item.to}\n${item.reason}'),
              isThreeLine: true,
              trailing: Chip(label: Text(item.status)),
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
              _list(_leaves),
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
}
