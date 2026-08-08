import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_api.dart';
import '../../team/application/team_api.dart';
import '../application/organization_admin_api.dart';

class GroupManagementScreen extends ConsumerStatefulWidget {
  const GroupManagementScreen({required this.session, super.key});

  final AuthSession session;

  @override
  ConsumerState<GroupManagementScreen> createState() =>
      _GroupManagementScreenState();
}

class _GroupManagementScreenState extends ConsumerState<GroupManagementScreen> {
  List<OrganizationGroup>? _groups;
  List<TeamMember> _members = <TeamMember>[];
  String? _error;

  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _groups = null;
      _error = null;
    });
    try {
      final values = await Future.wait<Object>(<Future<Object>>[
        ref.read(organizationAdminApiProvider).listGroups(widget.session),
        ref.read(teamApiProvider).list(widget.session),
      ]);
      if (mounted) {
        setState(() {
          _groups = values[0] as List<OrganizationGroup>;
          _members = values[1] as List<TeamMember>;
        });
      }
    } on DioException catch (error) {
      if (mounted) setState(() => _error = _groupProblemDetail(error));
    }
  }

  Future<void> _openEditor([OrganizationGroup? group]) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => GroupEditorScreen(
          session: widget.session,
          group: group,
          members: _members
              .where((member) => member.status == 'active')
              .toList(growable: false),
        ),
      ),
    );
    if (changed == true) await _load();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(_ar ? 'المجموعات التشغيلية' : 'Operational groups'),
    ),
    floatingActionButton: FloatingActionButton.extended(
      onPressed: _groups == null ? null : _openEditor,
      icon: const Icon(Icons.add),
      label: Text(_ar ? 'مجموعة' : 'Group'),
    ),
    body: _groups == null
        ? Center(
            child: _error == null
                ? const CircularProgressIndicator()
                : Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Text(_error!, textAlign: TextAlign.center),
                        const SizedBox(height: 12),
                        FilledButton(
                          onPressed: _load,
                          child: Text(_ar ? 'إعادة المحاولة' : 'Retry'),
                        ),
                      ],
                    ),
                  ),
          )
        : RefreshIndicator(
            onRefresh: _load,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
              children: <Widget>[
                Text(
                  _ar
                      ? 'أنشئ مجموعات عمل وعيّن أعضاءها لاستخدامها في النطاق والمهام وإثبات الحضور.'
                      : 'Create work groups and assign members for scope, tasks, and Proof of Presence.',
                ),
                const SizedBox(height: 16),
                if (_groups!.isEmpty)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Text(_ar ? 'لا توجد مجموعات.' : 'No groups yet.'),
                    ),
                  ),
                ..._groups!.map(
                  (group) => Card(
                    child: ListTile(
                      leading: Icon(
                        group.isActive
                            ? Icons.groups_outlined
                            : Icons.group_off_outlined,
                      ),
                      title: Text(group.name),
                      subtitle: Text(
                        '${group.code} · ${group.membershipIds.length} ${_ar ? 'أعضاء' : 'members'}',
                      ),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => _openEditor(group),
                    ),
                  ),
                ),
              ],
            ),
          ),
  );
}

class GroupEditorScreen extends ConsumerStatefulWidget {
  const GroupEditorScreen({
    required this.session,
    required this.group,
    required this.members,
    super.key,
  });

  final AuthSession session;
  final OrganizationGroup? group;
  final List<TeamMember> members;

  @override
  ConsumerState<GroupEditorScreen> createState() => _GroupEditorScreenState();
}

class _GroupEditorScreenState extends ConsumerState<GroupEditorScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _code = TextEditingController(
    text: widget.group?.code ?? '',
  );
  late final TextEditingController _name = TextEditingController(
    text: widget.group?.name ?? '',
  );
  late final TextEditingController _description = TextEditingController(
    text: widget.group?.description ?? '',
  );
  late final Set<String> _memberIds =
      widget.group?.membershipIds.toSet() ?? <String>{};
  late bool _active = widget.group?.isActive ?? true;
  bool _saving = false;

  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void dispose() {
    _code.dispose();
    _name.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      final api = ref.read(organizationAdminApiProvider);
      final existing = widget.group;
      final saved = existing == null
          ? await api.createGroup(
              widget.session,
              code: _code.text,
              name: _name.text,
              description: _description.text,
            )
          : await api.updateGroup(
              widget.session,
              OrganizationGroup(
                id: existing.id,
                name: _name.text.trim(),
                code: existing.code,
                description: _description.text.trim(),
                isActive: _active,
                version: existing.version,
                membershipIds: existing.membershipIds,
              ),
            );
      await api.replaceGroupMembers(widget.session, saved.id, _memberIds);
      if (mounted) Navigator.of(context).pop(true);
    } on DioException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(_groupProblemDetail(error))));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(
        widget.group == null
            ? (_ar ? 'مجموعة جديدة' : 'New group')
            : widget.group!.name,
      ),
    ),
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: <Widget>[
          TextFormField(
            controller: _code,
            enabled: widget.group == null,
            textCapitalization: TextCapitalization.characters,
            decoration: InputDecoration(
              labelText: _ar ? 'الرمز' : 'Code',
              border: const OutlineInputBorder(),
            ),
            validator: (value) =>
                RegExp(
                  r'^[A-Z0-9_-]{2,40}$',
                ).hasMatch((value ?? '').trim().toUpperCase())
                ? null
                : (_ar
                      ? 'استخدم حرفين أو أكثر: A-Z و0-9 و_ و-.'
                      : 'Use 2+ characters: A-Z, 0-9, _, or -.'),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _name,
            decoration: InputDecoration(
              labelText: _ar ? 'الاسم' : 'Name',
              border: const OutlineInputBorder(),
            ),
            validator: (value) => (value ?? '').trim().length >= 2
                ? null
                : (_ar ? 'أدخل اسم المجموعة.' : 'Enter a group name.'),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _description,
            maxLines: 3,
            decoration: InputDecoration(
              labelText: _ar ? 'الوصف' : 'Description',
              border: const OutlineInputBorder(),
            ),
          ),
          if (widget.group != null)
            SwitchListTile(
              value: _active,
              title: Text(_ar ? 'مجموعة نشطة' : 'Active group'),
              onChanged: (value) => setState(() => _active = value),
            ),
          const Divider(height: 32),
          Text(
            _ar ? 'الأعضاء' : 'Members',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          for (final member in widget.members)
            CheckboxListTile(
              value: _memberIds.contains(member.membershipId),
              title: Text(member.name),
              subtitle: Text(member.email),
              onChanged: (checked) => setState(
                () => checked == true
                    ? _memberIds.add(member.membershipId)
                    : _memberIds.remove(member.membershipId),
              ),
            ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _saving ? null : _save,
            icon: _saving
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.save_outlined),
            label: Text(_ar ? 'حفظ المجموعة' : 'Save group'),
          ),
        ],
      ),
    ),
  );
}

String _groupProblemDetail(DioException error) {
  final data = error.response?.data;
  if (data is Map<String, dynamic> && data['detail'] is String) {
    return data['detail'] as String;
  }
  return error.message ?? 'Request failed.';
}
