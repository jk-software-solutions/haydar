import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_api.dart';
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
      final tasks = await ref
          .read(taskApiProvider)
          .list(widget.session, allCompany: widget.managerMode);
      if (mounted) {
        setState(() {
          _tasks = tasks;
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
          error.message ??
          '$error';
    }
    return '$error';
  }

  Future<void> _change(WorkTask task, String status) async {
    String? reason;
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
    try {
      await ref
          .read(taskApiProvider)
          .updateStatus(widget.session, task, status, reason);
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

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: <Widget>[
          Text(
            _ar ? 'مهامي' : 'My tasks',
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
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
                  child: Icon(
                    task.priority == 'urgent'
                        ? Icons.priority_high_rounded
                        : Icons.task_alt_rounded,
                  ),
                ),
                title: Text(task.title),
                subtitle: Text(
                  '${task.status} · ${task.dueAt?.toLocal().toString().substring(0, 16) ?? '—'}',
                ),
                childrenPadding: const EdgeInsets.all(16),
                children: <Widget>[
                  Align(
                    alignment: AlignmentDirectional.centerStart,
                    child: Text(task.description),
                  ),
                  const SizedBox(height: 14),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: <Widget>[
                      ActionChip(
                        avatar: const Icon(Icons.forum_outlined),
                        label: Text(_ar ? 'التحديثات' : 'Updates'),
                        onPressed: () => _showComments(task),
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
  List<TaskComment> _comments = <TaskComment>[];
  bool _loading = true;
  bool _sending = false;
  String? _error;
  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  void dispose() {
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
    if (body.isEmpty || _sending) return;
    setState(() => _sending = true);
    try {
      await ref
          .read(taskApiProvider)
          .addComment(widget.session, widget.task.id, body);
      _controller.clear();
      await _refresh();
    } on Object catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _sending = false);
    }
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
                                    const SizedBox(height: 4),
                                    Text(
                                      item.createdAt
                                              ?.toLocal()
                                              .toString()
                                              .substring(0, 16) ??
                                          '',
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
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: InputDecoration(
                        hintText: _ar ? 'أضف تحديثًا' : 'Add an update',
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: _sending ? null : _send,
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
