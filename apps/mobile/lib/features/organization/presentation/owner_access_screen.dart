import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_api.dart';
import '../../team/application/team_api.dart';
import '../application/organization_admin_api.dart';

class _PermissionCopy {
  const _PermissionCopy(this.label, this.description);

  final String label;
  final String description;
}

const Map<String, ({_PermissionCopy ar, _PermissionCopy en})>
_permissionCopies = <String, ({_PermissionCopy ar, _PermissionCopy en})>{
  'members:view': (
    ar: _PermissionCopy('عرض الموظفين', 'عرض عضويات الشركة والدعوات.'),
    en: _PermissionCopy(
      'View employees',
      'View company memberships and invitations.',
    ),
  ),
  'members:create': (
    ar: _PermissionCopy('دعوة موظفين', 'إرسال دعوات لموظفين جدد.'),
    en: _PermissionCopy('Invite employees', 'Invite new company members.'),
  ),
  'members:manage': (
    ar: _PermissionCopy('إدارة الموظفين', 'تحديث العضويات والأدوار.'),
    en: _PermissionCopy(
      'Manage employees',
      'Update company memberships and roles.',
    ),
  ),
  'settings:manage': (
    ar: _PermissionCopy('إعدادات الشركة', 'تعديل إعدادات الشركة العامة.'),
    en: _PermissionCopy('Company settings', 'Manage company settings.'),
  ),
  'devices:view': (
    ar: _PermissionCopy(
      'عرض الأجهزة',
      'عرض أجهزة الموظفين وطلبات تغيير الجهاز.',
    ),
    en: _PermissionCopy(
      'View devices',
      'View device registrations and change requests.',
    ),
  ),
  'devices:manage': (
    ar: _PermissionCopy(
      'إدارة الأجهزة',
      'قبول أو رفض طلبات تغيير جهاز الموظف.',
    ),
    en: _PermissionCopy(
      'Manage devices',
      'Approve or reject employee device changes.',
    ),
  ),
  'branches:view': (
    ar: _PermissionCopy('عرض الفروع', 'عرض فروع الشركة.'),
    en: _PermissionCopy('View branches', 'View company branches.'),
  ),
  'branches:manage': (
    ar: _PermissionCopy('إدارة الفروع', 'إنشاء وتحديث فروع الشركة.'),
    en: _PermissionCopy(
      'Manage branches',
      'Create and update company branches.',
    ),
  ),
  'departments:view': (
    ar: _PermissionCopy('عرض الأقسام', 'عرض أقسام الشركة.'),
    en: _PermissionCopy('View departments', 'View company departments.'),
  ),
  'departments:manage': (
    ar: _PermissionCopy('إدارة الأقسام', 'إنشاء وتحديث أقسام الشركة.'),
    en: _PermissionCopy(
      'Manage departments',
      'Create and update company departments.',
    ),
  ),
  'assignments:view': (
    ar: _PermissionCopy('عرض التعيينات', 'عرض سجل تعيين الموظفين على الفروع.'),
    en: _PermissionCopy(
      'View assignments',
      'View employee branch assignment history.',
    ),
  ),
  'assignments:manage': (
    ar: _PermissionCopy('إدارة التعيينات', 'تعيين ونقل الموظفين بين الفروع.'),
    en: _PermissionCopy(
      'Manage assignments',
      'Assign and transfer employees between branches.',
    ),
  ),
  'shifts:view': (
    ar: _PermissionCopy('عرض الورديات', 'عرض ورديات الشركة وتعييناتها.'),
    en: _PermissionCopy('View shifts', 'View company shifts and assignments.'),
  ),
  'shifts:manage': (
    ar: _PermissionCopy('إدارة الورديات', 'إنشاء وتعيين ورديات الشركة.'),
    en: _PermissionCopy('Manage shifts', 'Create and assign company shifts.'),
  ),
  'attendance:view': (
    ar: _PermissionCopy('عرض الحضور', 'عرض سجلات حضور وانصراف الموظفين.'),
    en: _PermissionCopy('View attendance', 'View tenant attendance records.'),
  ),
  'attendance:manage': (
    ar: _PermissionCopy('إدارة الحضور', 'إنشاء وتصحيح سجلات الحضور.'),
    en: _PermissionCopy(
      'Manage attendance',
      'Create and correct attendance records.',
    ),
  ),
  'permissions:view': (
    ar: _PermissionCopy('عرض الاستئذانات', 'عرض طلبات استئذان الموظفين.'),
    en: _PermissionCopy(
      'View permissions',
      'View employee permission requests.',
    ),
  ),
  'permissions:manage': (
    ar: _PermissionCopy(
      'إدارة الاستئذانات',
      'مراجعة طلبات الاستئذان وقبولها أو رفضها.',
    ),
    en: _PermissionCopy(
      'Manage permissions',
      'Review employee permission requests.',
    ),
  ),
  'presence:manage': (
    ar: _PermissionCopy('إثبات التواجد', 'إنشاء ومراجعة طلبات إثبات التواجد.'),
    en: _PermissionCopy(
      'Proof of presence',
      'Create and review presence requests.',
    ),
  ),
  'geofence_exits:view': (
    ar: _PermissionCopy(
      'عرض مغادرة النطاق',
      'عرض أحداث مغادرة النطاق غير المصرح بها.',
    ),
    en: _PermissionCopy(
      'View geofence exits',
      'View unauthorized geofence exit events.',
    ),
  ),
  'geofence_exits:manage': (
    ar: _PermissionCopy(
      'إدارة مغادرة النطاق',
      'مراجعة أحداث مغادرة النطاق غير المصرح بها.',
    ),
    en: _PermissionCopy(
      'Manage geofence exits',
      'Review unauthorized geofence exit events.',
    ),
  ),
  'tasks:view': (
    ar: _PermissionCopy('عرض المهام', 'عرض المهام المسندة.'),
    en: _PermissionCopy('View tasks', 'View assigned tenant tasks.'),
  ),
  'tasks:manage': (
    ar: _PermissionCopy('إدارة المهام', 'إنشاء وإدارة مهام العمل.'),
    en: _PermissionCopy('Manage tasks', 'Create and manage tenant tasks.'),
  ),
  'leave:view': (
    ar: _PermissionCopy('عرض الإجازات', 'عرض طلبات الإجازة والأرصدة.'),
    en: _PermissionCopy(
      'View leave',
      'View tenant leave requests and balances.',
    ),
  ),
  'leave:manage': (
    ar: _PermissionCopy(
      'إدارة الإجازات',
      'إدارة أنواع الإجازات والأرصدة والموافقات.',
    ),
    en: _PermissionCopy(
      'Manage leave',
      'Manage leave types, balances, and approvals.',
    ),
  ),
  'documents:view': (
    ar: _PermissionCopy('عرض الوثائق', 'عرض وثائق الموظفين.'),
    en: _PermissionCopy('View documents', 'View tenant employee documents.'),
  ),
  'documents:manage': (
    ar: _PermissionCopy('إدارة الوثائق', 'إدارة ومراجعة وثائق الموظفين.'),
    en: _PermissionCopy(
      'Manage documents',
      'Manage and review employee documents.',
    ),
  ),
  'reports:view': (
    ar: _PermissionCopy('عرض التقارير', 'عرض تقارير القوى العاملة.'),
    en: _PermissionCopy('View reports', 'View tenant workforce reports.'),
  ),
  'reports:export': (
    ar: _PermissionCopy('تصدير التقارير', 'تصدير التقارير إلى ملفات.'),
    en: _PermissionCopy('Export reports', 'Export tenant reports.'),
  ),
  'subscription:view': (
    ar: _PermissionCopy('عرض الاشتراك', 'عرض اشتراك الشركة.'),
    en: _PermissionCopy('View subscription', 'View the company subscription.'),
  ),
  'subscription:manage': (
    ar: _PermissionCopy('إدارة الاشتراك', 'إدارة طلبات اشتراك الشركة.'),
    en: _PermissionCopy(
      'Manage subscription',
      'Manage company subscription requests.',
    ),
  ),
};

_PermissionCopy _permissionCopy(PermissionOption permission, bool ar) {
  final copy = _permissionCopies[permission.code];
  return copy == null
      ? _PermissionCopy(permission.code, permission.description)
      : ar
      ? copy.ar
      : copy.en;
}

class OwnerAccessScreen extends ConsumerStatefulWidget {
  const OwnerAccessScreen({required this.session, super.key});

  final AuthSession session;

  @override
  ConsumerState<OwnerAccessScreen> createState() => _OwnerAccessScreenState();
}

class _OwnerAccessScreenState extends ConsumerState<OwnerAccessScreen> {
  OwnerAccessData? _data;
  String? _error;

  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _data = null;
      _error = null;
    });
    try {
      final data = await ref
          .read(organizationAdminApiProvider)
          .loadOwnerAccess(widget.session);
      if (mounted) setState(() => _data = data);
    } on DioException catch (error) {
      if (mounted) setState(() => _error = _problemDetail(error));
    }
  }

  @override
  Widget build(BuildContext context) {
    final data = _data;
    return Scaffold(
      appBar: AppBar(
        title: Text(_ar ? 'الأدوار والصلاحيات' : 'Roles and access'),
      ),
      body: data == null
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
                padding: const EdgeInsets.all(20),
                children: <Widget>[
                  Text(
                    _ar
                        ? 'عيّن أدوار كل عضو وصلاحياته ونطاق الفروع والأقسام والمجموعات.'
                        : 'Assign each member’s roles, permission overrides, and branch, department, and group scope.',
                  ),
                  const SizedBox(height: 16),
                  ...data.members.map((member) {
                    final access = data.access
                        .where(
                          (item) => item.membershipId == member.membershipId,
                        )
                        .firstOrNull;
                    final owner =
                        access?.roleCodes.contains('OWNER') ??
                        member.role == 'OWNER';
                    return Card(
                      child: ListTile(
                        leading: const Icon(
                          Icons.admin_panel_settings_outlined,
                        ),
                        title: Text(member.name),
                        subtitle: Text(
                          '${access?.roleCodes.join(', ') ?? member.role}\n${member.email}',
                        ),
                        isThreeLine: true,
                        trailing: owner
                            ? const Icon(Icons.lock_outline)
                            : const Icon(Icons.chevron_right),
                        onTap: owner || access == null
                            ? null
                            : () async {
                                final changed = await Navigator.of(context)
                                    .push<bool>(
                                      MaterialPageRoute<bool>(
                                        builder: (_) =>
                                            MemberAccessEditorScreen(
                                              session: widget.session,
                                              member: member,
                                              access: access,
                                              data: data,
                                            ),
                                      ),
                                    );
                                if (changed == true) await _load();
                              },
                      ),
                    );
                  }),
                ],
              ),
            ),
    );
  }
}

class MemberAccessEditorScreen extends ConsumerStatefulWidget {
  const MemberAccessEditorScreen({
    required this.session,
    required this.member,
    required this.access,
    required this.data,
    super.key,
  });

  final AuthSession session;
  final TeamMember member;
  final MemberAccess access;
  final OwnerAccessData data;

  @override
  ConsumerState<MemberAccessEditorScreen> createState() =>
      _MemberAccessEditorScreenState();
}

class _MemberAccessEditorScreenState
    extends ConsumerState<MemberAccessEditorScreen> {
  late final Set<String> _roles = widget.access.roleCodes.toSet();
  late final Map<String, bool> _overrides = Map<String, bool>.from(
    widget.access.permissionOverrides,
  );
  late final Set<String> _branches = widget.access.branchIds.toSet();
  late final Set<String> _departments = widget.access.departmentIds.toSet();
  late final Set<String> _groups = widget.access.groupIds.toSet();
  bool _saving = false;

  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  Future<void> _save() async {
    if (_roles.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _ar ? 'اختر دوراً واحداً على الأقل.' : 'Select at least one role.',
          ),
        ),
      );
      return;
    }
    setState(() => _saving = true);
    try {
      await ref
          .read(organizationAdminApiProvider)
          .updateMemberAccess(
            widget.session,
            MemberAccess(
              membershipId: widget.access.membershipId,
              roleCodes: _roles.toList(growable: false),
              permissionOverrides: _overrides,
              effectivePermissions: widget.access.effectivePermissions,
              branchIds: _branches.toList(growable: false),
              departmentIds: _departments.toList(growable: false),
              groupIds: _groups.toList(growable: false),
            ),
          );
      if (mounted) Navigator.of(context).pop(true);
    } on DioException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(_problemDetail(error))));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(widget.member.name),
      actions: <Widget>[
        TextButton(
          onPressed: _saving ? null : _save,
          child: Text(_ar ? 'حفظ' : 'Save'),
        ),
      ],
    ),
    body: ListView(
      padding: const EdgeInsets.all(20),
      children: <Widget>[
        Text(
          _ar ? 'الأدوار' : 'Roles',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        for (final role in const <String>[
          'MANAGER',
          'SUPERVISOR',
          'HR_OFFICER',
          'EMPLOYEE',
        ])
          CheckboxListTile(
            value: _roles.contains(role),
            title: Text(_roleLabel(role)),
            onChanged: (selected) => setState(
              () => selected == true ? _roles.add(role) : _roles.remove(role),
            ),
          ),
        const Divider(),
        Text(
          _ar ? 'تخصيص الصلاحيات' : 'Permission overrides',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 8),
        for (final permission in widget.data.permissions)
          Builder(
            builder: (context) {
              final copy = _permissionCopy(permission, _ar);
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: DropdownButtonFormField<String>(
                  initialValue: !_overrides.containsKey(permission.code)
                      ? 'inherit'
                      : _overrides[permission.code]!
                      ? 'allow'
                      : 'deny',
                  decoration: InputDecoration(
                    labelText: copy.label,
                    helperText: copy.description,
                    border: const OutlineInputBorder(),
                  ),
                  items: <DropdownMenuItem<String>>[
                    DropdownMenuItem(
                      value: 'inherit',
                      child: Text(_ar ? 'حسب الدور' : 'Inherit role'),
                    ),
                    DropdownMenuItem(
                      value: 'allow',
                      child: Text(_ar ? 'سماح' : 'Allow'),
                    ),
                    DropdownMenuItem(
                      value: 'deny',
                      child: Text(_ar ? 'منع' : 'Deny'),
                    ),
                  ],
                  onChanged: (value) => setState(() {
                    if (value == 'inherit') {
                      _overrides.remove(permission.code);
                    } else {
                      _overrides[permission.code] = value == 'allow';
                    }
                  }),
                ),
              );
            },
          ),
        _ScopeEditor(
          title: _ar ? 'نطاق الفروع' : 'Branch scope',
          options: widget.data.branches,
          selected: _branches,
          onChanged: () => setState(() {}),
        ),
        _ScopeEditor(
          title: _ar ? 'نطاق الأقسام' : 'Department scope',
          options: widget.data.departments,
          selected: _departments,
          onChanged: () => setState(() {}),
        ),
        _ScopeEditor(
          title: _ar ? 'نطاق المجموعات' : 'Group scope',
          options: widget.data.groups,
          selected: _groups,
          onChanged: () => setState(() {}),
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
          label: Text(_ar ? 'حفظ الوصول' : 'Save access'),
        ),
      ],
    ),
  );

  String _roleLabel(String role) => switch (role) {
    'MANAGER' => _ar ? 'مدير' : 'Manager',
    'SUPERVISOR' => _ar ? 'مشرف' : 'Supervisor',
    'HR_OFFICER' => _ar ? 'موارد بشرية' : 'HR officer',
    _ => _ar ? 'موظف' : 'Employee',
  };
}

class _ScopeEditor extends StatelessWidget {
  const _ScopeEditor({
    required this.title,
    required this.options,
    required this.selected,
    required this.onChanged,
  });

  final String title;
  final List<NamedOption> options;
  final Set<String> selected;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) => ExpansionTile(
    title: Text(title),
    subtitle: Text('${selected.length}/${options.length}'),
    children: options
        .map(
          (option) => CheckboxListTile(
            value: selected.contains(option.id),
            title: Text(option.name),
            onChanged: (checked) {
              checked == true
                  ? selected.add(option.id)
                  : selected.remove(option.id);
              onChanged();
            },
          ),
        )
        .toList(growable: false),
  );
}

String _problemDetail(DioException error) {
  final data = error.response?.data;
  if (data is Map<String, dynamic> && data['detail'] is String) {
    return data['detail'] as String;
  }
  return error.message ?? 'Request failed.';
}
