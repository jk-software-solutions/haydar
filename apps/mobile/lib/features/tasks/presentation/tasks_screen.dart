import 'dart:async';

import 'package:file_selector/file_selector.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../../auth/application/auth_api.dart';
import '../../../app/theme/app_theme.dart';
import '../../../core/network/api_client.dart';
import '../application/task_api.dart';

class TasksScreen extends ConsumerStatefulWidget {
  const TasksScreen({
    required this.session,
    this.managerMode = false,
    super.key,
  });
  final AuthSession session;
  final bool managerMode;

  @override
  ConsumerState<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends ConsumerState<TasksScreen> {
  List<WorkTask> _tasks = <WorkTask>[];
  List<TaskRecipient> _recipients = <TaskRecipient>[];
  Timer? _refreshTimer;
  bool _loading = true;
  String? _error;
  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  static const XTypeGroup _evidenceTypes = XTypeGroup(
    label: 'DawamTech evidence',
    extensions: <String>[
      'jpg',
      'jpeg',
      'png',
      'webp',
      'pdf',
      'txt',
      'docx',
      'xlsx',
      'aac',
      'm4a',
      'mp3',
      'ogg',
      'wav',
      '3gp',
    ],
  );

  @override
  void initState() {
    super.initState();
    _refresh();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 15),
      (_) => _refresh(),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final api = ref.read(taskApiProvider);
      final tasks = await api.list(
        widget.session,
        allCompany: widget.managerMode,
      );
      List<TaskRecipient> recipients = <TaskRecipient>[];
      try {
        recipients = await api.recipients(widget.session);
      } on Object catch (_) {
        // Older servers can still list tasks while the recipient endpoint is
        // being deployed; keep the task screen usable in that case.
      }
      if (mounted) {
        setState(() {
          _tasks = tasks;
          _recipients = recipients;
          _error = null;
        });
      }
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _createTask() async {
    if (_recipients.isEmpty) return;
    final titleController = TextEditingController();
    final descriptionController = TextEditingController();
    var priority = 'normal';
    var recipientId = _recipients.first.id;
    final draft =
        await showDialog<
          ({
            String title,
            String description,
            String priority,
            String recipientId,
          })
        >(
          context: context,
          builder: (context) => StatefulBuilder(
            builder: (context, setDialogState) => AlertDialog(
              title: Text(_ar ? 'إرسال مهمة' : 'Send a task'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    TextField(
                      controller: titleController,
                      decoration: InputDecoration(
                        labelText: _ar ? 'عنوان المهمة' : 'Task title',
                      ),
                    ),
                    TextField(
                      controller: descriptionController,
                      maxLines: 4,
                      decoration: InputDecoration(
                        labelText: _ar ? 'التفاصيل' : 'Details',
                      ),
                    ),
                    DropdownButtonFormField<String>(
                      initialValue: recipientId,
                      decoration: InputDecoration(
                        labelText: _ar ? 'إرسال إلى' : 'Send to',
                      ),
                      items: _recipients
                          .map(
                            (recipient) => DropdownMenuItem<String>(
                              value: recipient.id,
                              child: Text(
                                '${recipient.displayName} · ${recipient.email}',
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          )
                          .toList(growable: false),
                      onChanged: (value) {
                        if (value != null) {
                          setDialogState(() => recipientId = value);
                        }
                      },
                    ),
                    DropdownButtonFormField<String>(
                      initialValue: priority,
                      decoration: InputDecoration(
                        labelText: _ar ? 'الأولوية' : 'Priority',
                      ),
                      items: <DropdownMenuItem<String>>[
                        DropdownMenuItem(
                          value: 'normal',
                          child: Text(_ar ? 'عادية' : 'Normal'),
                        ),
                        DropdownMenuItem(
                          value: 'high',
                          child: Text(_ar ? 'عالية' : 'High'),
                        ),
                        DropdownMenuItem(
                          value: 'urgent',
                          child: Text(_ar ? 'عاجلة' : 'Urgent'),
                        ),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          setDialogState(() => priority = value);
                        }
                      },
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
                  onPressed: () {
                    final title = titleController.text.trim();
                    final description = descriptionController.text.trim();
                    if (title.length < 2 || description.length < 2) return;
                    Navigator.pop(context, (
                      title: title,
                      description: description,
                      priority: priority,
                      recipientId: recipientId,
                    ));
                  },
                  child: Text(_ar ? 'إرسال' : 'Send'),
                ),
              ],
            ),
          ),
        );
    titleController.dispose();
    descriptionController.dispose();
    if (draft == null || !mounted) return;
    try {
      await ref
          .read(taskApiProvider)
          .create(
            widget.session,
            title: draft.title,
            description: draft.description,
            priority: draft.priority,
            recipientId: draft.recipientId,
          );
      await _refresh();
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    }
  }

  String _message(Object error) {
    if (error is DioException && error.response?.data is Map<String, dynamic>) {
      return ((error.response!.data as Map<String, dynamic>)['detail']
              as String?) ??
          error.message ??
          '$error';
    }
    return '$error';
  }

  Future<String?> _pickAndUploadFile() async {
    final file = await openFile(
      acceptedTypeGroups: <XTypeGroup>[_evidenceTypes],
    );
    if (file == null) return null;
    final bytes = await file.readAsBytes();
    if (bytes.isEmpty) return null;
    final fileId = await ref
        .read(taskApiProvider)
        .upload(widget.session, filename: file.name, bytes: bytes);
    return fileId.isEmpty ? null : fileId;
  }

  Future<void> _completeWithReceipt(WorkTask task) async {
    try {
      final fileId = await _pickAndUploadFile();
      if (fileId == null || !mounted) return;
      await ref
          .read(taskApiProvider)
          .updateStatus(widget.session, task, 'completed', null, null, fileId);
      await _refresh();
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    }
  }

  Future<void> _openAttachment(String fileId) async {
    final controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..loadRequest(
        Uri.parse(
          '${apiBaseUrl.replaceFirst(RegExp(r'/+$'), '')}/files/$fileId',
        ),
        headers: <String, String>{
          'Authorization': 'Bearer ${widget.session.accessToken}',
        },
      );
    if (!mounted) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => Scaffold(
          appBar: AppBar(title: Text(_ar ? 'مرفق المهمة' : 'Task attachment')),
          body: WebViewWidget(controller: controller),
        ),
      ),
    );
  }

  Future<void> _change(WorkTask task, String status) async {
    String? reason;
    DateTime? requestedDueAt;
    if (<String>{'blocked', 'postponed', 'needs_more_time'}.contains(status)) {
      final controller = TextEditingController();
      reason = await showDialog<String>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(_ar ? 'اكتب السبب' : 'Provide a reason'),
          content: TextField(controller: controller, maxLines: 3),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(_ar ? 'إلغاء' : 'Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, controller.text.trim()),
              child: Text(_ar ? 'حفظ' : 'Save'),
            ),
          ],
        ),
      );
      controller.dispose();
      if (reason == null || reason.isEmpty) return;
    }
    if (status == 'needs_more_time') {
      if (!mounted) return;
      final date = await showDatePicker(
        context: context,
        initialDate: (task.dueAt ?? DateTime.now()).add(
          const Duration(days: 1),
        ),
        firstDate: DateTime.now(),
        lastDate: DateTime.now().add(const Duration(days: 365)),
      );
      if (date == null) return;
      requestedDueAt = DateTime(date.year, date.month, date.day, 17);
    }
    try {
      await ref
          .read(taskApiProvider)
          .updateStatus(
            widget.session,
            task,
            status,
            reason,
            requestedDueAt,
            null,
          );
      await _refresh();
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    }
  }

  Future<void> _decideExtension(WorkTask task, String decision) async {
    DateTime? newDueAt;
    if (decision == 'approved') {
      final date = await showDatePicker(
        context: context,
        initialDate:
            task.latestExtension?.requestedDueAt?.toLocal() ??
            DateTime.now().add(const Duration(days: 1)),
        firstDate: DateTime.now(),
        lastDate: DateTime.now().add(const Duration(days: 365)),
      );
      if (date == null) return;
      newDueAt = DateTime(date.year, date.month, date.day, 17);
    }
    if (!mounted) return;
    final controller = TextEditingController();
    final comment = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(_ar ? 'تعليق قرار التمديد' : 'Extension decision comment'),
        content: TextField(controller: controller, maxLines: 3),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(_ar ? 'إلغاء' : 'Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: Text(_ar ? 'حفظ القرار' : 'Save decision'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (comment == null || comment.length < 2) return;
    try {
      await ref
          .read(taskApiProvider)
          .decideExtension(
            widget.session,
            task,
            decision: decision,
            comment: comment,
            newDueAt: newDueAt,
          );
      await _refresh();
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    }
  }

  Future<void> _showComments(WorkTask task) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => TaskCommentsSheet(session: widget.session, task: task),
    );
  }

  String _statusLabel(String status) => switch (status) {
    'new' => _ar ? 'جديدة' : 'New',
    'viewed' => _ar ? 'تم الاستلام' : 'Received',
    'in_progress' => _ar ? 'قيد التنفيذ' : 'In progress',
    'completed' => _ar ? 'مكتملة' : 'Completed',
    'needs_more_time' => _ar ? 'تحتاج وقتًا إضافيًا' : 'Needs more time',
    'blocked' => _ar ? 'متعطلة' : 'Blocked',
    'postponed' => _ar ? 'مؤجلة' : 'Postponed',
    _ => status,
  };

  String _priorityLabel(String priority) => switch (priority) {
    'low' => _ar ? 'منخفضة' : 'Low',
    'high' => _ar ? 'عالية' : 'High',
    'urgent' => _ar ? 'عاجلة' : 'Urgent',
    _ => _ar ? 'عادية' : 'Normal',
  };

  String _formatDate(DateTime? value) {
    if (value == null) return '—';
    final local = value.toLocal();
    final hour = local.hour.toString().padLeft(2, '0');
    final minute = local.minute.toString().padLeft(2, '0');
    return '${local.day.toString().padLeft(2, '0')}/'
        '${local.month.toString().padLeft(2, '0')}/${local.year} $hour:$minute';
  }

  Color _statusColor(BuildContext context, String status) {
    final scheme = Theme.of(context).colorScheme;
    return switch (status) {
      'completed' => AppColors.success,
      'in_progress' => scheme.primary,
      'viewed' => AppColors.blue,
      'needs_more_time' => const Color(0xFFB45309),
      'blocked' => AppColors.error,
      'postponed' => const Color(0xFF7C3AED),
      _ => scheme.outline,
    };
  }

  Widget _statusBadge(BuildContext context, String status) {
    final color = _statusColor(context, status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: .35)),
      ),
      child: Text(
        _statusLabel(status),
        style: TextStyle(color: color, fontWeight: FontWeight.w800),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  widget.managerMode
                      ? (_ar ? 'المهام' : 'Tasks')
                      : (_ar ? 'مهامي وطلباتي' : 'My tasks and requests'),
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              FilledButton.icon(
                onPressed: _recipients.isEmpty ? null : _createTask,
                icon: const Icon(Icons.add_task_rounded),
                label: Text(
                  widget.managerMode
                      ? (_ar ? 'مهمة' : 'Task')
                      : (_ar ? 'طلب مهمة' : 'Request'),
                ),
              ),
            ],
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          if (_tasks.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Text(_ar ? 'لا توجد مهام.' : 'No tasks assigned.'),
              ),
            ),
          ..._tasks.map(
            (task) => Card(
              child: ExpansionTile(
                leading: CircleAvatar(
                  backgroundColor: _statusColor(
                    context,
                    task.status,
                  ).withValues(alpha: .14),
                  child: Icon(
                    task.priority == 'urgent'
                        ? Icons.priority_high_rounded
                        : Icons.task_alt_rounded,
                    color: _statusColor(context, task.status),
                  ),
                ),
                title: Text(task.title),
                subtitle: Text(
                  '${_formatDate(task.dueAt)} · ${_priorityLabel(task.priority)}',
                ),
                childrenPadding: const EdgeInsets.all(16),
                children: <Widget>[
                  Align(
                    alignment: AlignmentDirectional.centerStart,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        _statusBadge(context, task.status),
                        const SizedBox(height: 8),
                        Text(task.description),
                        const SizedBox(height: 6),
                        Text(
                          '${_ar ? 'الأولوية' : 'Priority'}: ${_priorityLabel(task.priority)}',
                          style: Theme.of(context).textTheme.labelMedium,
                        ),
                        if (task.completionAttachmentFileId != null)
                          Row(
                            children: <Widget>[
                              Icon(
                                Icons.attachment_rounded,
                                size: 18,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Text(
                                  _ar
                                      ? 'أرفق الموظف إيصال الإنجاز.'
                                      : 'The employee attached completion evidence.',
                                  style: TextStyle(
                                    color: Theme.of(
                                      context,
                                    ).colorScheme.primary,
                                  ),
                                ),
                              ),
                              TextButton.icon(
                                onPressed: () => _openAttachment(
                                  task.completionAttachmentFileId!,
                                ),
                                icon: const Icon(Icons.open_in_new_rounded),
                                label: Text(_ar ? 'فتح' : 'Open'),
                              ),
                            ],
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  if (task.latestExtension != null) ...<Widget>[
                    Card(
                      child: ListTile(
                        title: Text(
                          _ar ? 'طلب وقت إضافي' : 'Extension request',
                        ),
                        subtitle: Text(
                          '${task.latestExtension!.reason}\n${task.latestExtension!.status} · ${task.latestExtension!.requestedDueAt?.toLocal() ?? '—'}',
                        ),
                        isThreeLine: true,
                      ),
                    ),
                    if (widget.managerMode &&
                        task.latestExtension!.status == 'pending')
                      Wrap(
                        spacing: 8,
                        children: <Widget>[
                          FilledButton(
                            onPressed: () => _decideExtension(task, 'approved'),
                            child: Text(_ar ? 'موافقة وتمديد' : 'Approve'),
                          ),
                          OutlinedButton(
                            onPressed: () => _decideExtension(task, 'rejected'),
                            child: Text(_ar ? 'رفض التمديد' : 'Reject'),
                          ),
                        ],
                      ),
                  ],
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: <Widget>[
                      ActionChip(
                        avatar: const Icon(Icons.forum_outlined),
                        label: Text(_ar ? 'التحديثات' : 'Updates'),
                        onPressed: () => _showComments(task),
                      ),
                      if (task.status == 'new')
                        ActionChip(
                          label: Text(_ar ? 'استلمت المهمة' : 'I received it'),
                          onPressed: () => _change(task, 'viewed'),
                        ),
                      ActionChip(
                        label: Text(_ar ? 'قيد التنفيذ' : 'In progress'),
                        onPressed: () => _change(task, 'in_progress'),
                      ),
                      ActionChip(
                        label: Text(_ar ? 'مكتملة' : 'Complete'),
                        onPressed: () => _change(task, 'completed'),
                      ),
                      ActionChip(
                        avatar: const Icon(Icons.receipt_long_rounded),
                        label: Text(
                          _ar
                              ? 'إنهاء وإرفاق الإيصال'
                              : 'Complete with receipt',
                        ),
                        onPressed: () => _completeWithReceipt(task),
                      ),
                      ActionChip(
                        label: Text(_ar ? 'وقت إضافي' : 'More time'),
                        onPressed: () => _change(task, 'needs_more_time'),
                      ),
                      ActionChip(
                        label: Text(_ar ? 'متعطلة' : 'Blocked'),
                        onPressed: () => _change(task, 'blocked'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class TaskCommentsSheet extends ConsumerStatefulWidget {
  const TaskCommentsSheet({
    required this.session,
    required this.task,
    super.key,
  });
  final AuthSession session;
  final WorkTask task;

  @override
  ConsumerState<TaskCommentsSheet> createState() => _TaskCommentsSheetState();
}

class _TaskCommentsSheetState extends ConsumerState<TaskCommentsSheet> {
  final _controller = TextEditingController();
  Timer? _refreshTimer;
  List<TaskComment> _comments = <TaskComment>[];
  bool _loading = true;
  bool _sending = false;
  bool _uploading = false;
  String? _attachmentFileId;
  String? _attachmentName;
  String? _error;
  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _refresh();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 15),
      (_) => _refresh(),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final comments = await ref
          .read(taskApiProvider)
          .comments(widget.session, widget.task.id);
      if (mounted) {
        setState(() {
          _comments = comments;
          _error = null;
        });
      }
    } on Object catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _send() async {
    final body = _controller.text.trim();
    if ((body.isEmpty && _attachmentFileId == null) || _sending) return;
    setState(() => _sending = true);
    try {
      await ref
          .read(taskApiProvider)
          .addComment(
            widget.session,
            widget.task.id,
            body.isEmpty ? (_ar ? 'مرفق' : 'Attachment') : body,
            attachmentFileId: _attachmentFileId,
          );
      _controller.clear();
      setState(() {
        _attachmentFileId = null;
        _attachmentName = null;
      });
      await _refresh();
    } on Object catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _pickAttachment() async {
    if (_uploading || _sending) return;
    try {
      final file = await openFile(
        acceptedTypeGroups: <XTypeGroup>[_TasksScreenState._evidenceTypes],
      );
      if (file == null) return;
      final bytes = await file.readAsBytes();
      if (bytes.isEmpty) return;
      setState(() => _uploading = true);
      final fileId = await ref
          .read(taskApiProvider)
          .upload(widget.session, filename: file.name, bytes: bytes);
      if (!mounted) return;
      setState(() {
        _attachmentFileId = fileId.isEmpty ? null : fileId;
        _attachmentName = fileId.isEmpty ? null : file.name;
      });
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  String _message(Object error) {
    if (error is DioException && error.response?.data is Map<String, dynamic>) {
      return ((error.response!.data as Map<String, dynamic>)['detail']
              as String?) ??
          error.message ??
          '$error';
    }
    return '$error';
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
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          20,
          16,
          20,
          MediaQuery.viewInsetsOf(context).bottom + 20,
        ),
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * .7,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Text(
                widget.task.title,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              if (_error != null)
                Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              Expanded(
                child: _loading
                    ? const Center(child: CircularProgressIndicator())
                    : _comments.isEmpty
                    ? Center(
                        child: Text(
                          _ar ? 'لا توجد تحديثات.' : 'No updates yet.',
                        ),
                      )
                    : ListView.builder(
                        itemCount: _comments.length,
                        itemBuilder: (context, index) {
                          final item = _comments[index];
                          final mine =
                              item.authorMembershipId ==
                              widget.session.membershipId;
                          return Align(
                            alignment: mine
                                ? AlignmentDirectional.centerEnd
                                : AlignmentDirectional.centerStart,
                            child: Card(
                              color: mine
                                  ? Theme.of(
                                      context,
                                    ).colorScheme.primaryContainer
                                  : null,
                              child: Padding(
                                padding: const EdgeInsets.all(12),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Text(item.body),
                                    if (item.attachmentFileId != null)
                                      Padding(
                                        padding: const EdgeInsets.only(top: 6),
                                        child: Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: <Widget>[
                                            const Icon(
                                              Icons.attach_file,
                                              size: 16,
                                            ),
                                            const SizedBox(width: 4),
                                            Text(_ar ? 'مرفق' : 'Attachment'),
                                          ],
                                        ),
                                      ),
                                    const SizedBox(height: 4),
                                    Text(
                                      _formatDateTime(item.createdAt),
                                      style: Theme.of(
                                        context,
                                      ).textTheme.labelSmall,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          );
                        },
                      ),
              ),
              Row(
                children: <Widget>[
                  IconButton(
                    tooltip: _ar
                        ? 'إرفاق ملف أو تسجيل صوتي'
                        : 'Attach a file or audio',
                    onPressed: _uploading || _sending ? null : _pickAttachment,
                    icon: _uploading
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.attach_file_rounded),
                  ),
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: InputDecoration(
                        hintText: _ar ? 'أضف تحديثًا' : 'Add an update',
                      ),
                    ),
                  ),
                  if (_attachmentName != null)
                    Flexible(
                      child: Text(
                        _attachmentName!,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    ),
                  IconButton(
                    onPressed: _sending || _uploading ? null : _send,
                    icon: const Icon(Icons.send_rounded),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
