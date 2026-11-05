import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_api.dart';
import '../application/team_api.dart';

class TeamScreen extends ConsumerStatefulWidget {
  const TeamScreen({required this.session, super.key});
  final AuthSession session;

  @override
  ConsumerState<TeamScreen> createState() => _TeamScreenState();
}

class _TeamScreenState extends ConsumerState<TeamScreen> {
  List<TeamMember> _members = <TeamMember>[];
  final _searchController = TextEditingController();
  String _search = '';
  bool _loading = true;
  String? _error;
  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final members = await ref.read(teamApiProvider).list(widget.session);
      if (mounted) {
        setState(() {
          _members = members;
          _error = null;
        });
      }
    } on DioException catch (error) {
      final data = error.response?.data;
      if (mounted) {
        setState(
          () => _error = data is Map<String, dynamic>
              ? _friendlyError(
                  data['code'] as String?,
                  data['detail'] as String?,
                )
              : (_ar
                    ? 'تعذر تحميل فريق الشركة.'
                    : 'The company team could not be loaded.'),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    final visibleMembers = _members
        .where((member) {
          final query = _search.trim().toLowerCase();
          return query.isEmpty ||
              member.name.toLowerCase().contains(query) ||
              member.email.toLowerCase().contains(query) ||
              (member.jobTitle?.toLowerCase().contains(query) ?? false);
        })
        .toList(growable: false);
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: <Widget>[
          Text(
            _ar ? 'فريق الشركة' : 'Company team',
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _searchController,
            onChanged: (value) => setState(() => _search = value),
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: _ar
                  ? 'ابحث بالاسم أو البريد'
                  : 'Search by name or email',
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: _search.isEmpty
                  ? null
                  : IconButton(
                      tooltip: _ar ? 'مسح البحث' : 'Clear search',
                      onPressed: () {
                        _searchController.clear();
                        setState(() => _search = '');
                      },
                      icon: const Icon(Icons.clear_rounded),
                    ),
            ),
          ),
          const SizedBox(height: 12),
          if (_error != null)
            Card(
              color: Theme.of(context).colorScheme.errorContainer,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(_error!),
              ),
            ),
          if (_members.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Text(
                  _ar ? 'لا يوجد موظفون حتى الآن.' : 'No employees yet.',
                ),
              ),
            ),
          if (_members.isNotEmpty && visibleMembers.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Text(
                  _ar ? 'لا توجد نتائج مطابقة.' : 'No matching employees.',
                ),
              ),
            ),
          ...visibleMembers.map(
            (member) => Card(
              child: ListTile(
                leading: CircleAvatar(
                  child: Text(
                    member.name.isEmpty ? '?' : member.name.characters.first,
                  ),
                ),
                title: Text(member.name),
                subtitle: Text(
                  '${member.jobTitle ?? _roleLabel(member.role)}\n${member.email}',
                ),
                isThreeLine: true,
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: <Widget>[
                    Chip(
                      label: Text(_statusLabel(member.status)),
                      visualDensity: VisualDensity.compact,
                      side: BorderSide.none,
                      backgroundColor: member.status == 'active'
                          ? Theme.of(context).colorScheme.primaryContainer
                          : Theme.of(
                              context,
                            ).colorScheme.surfaceContainerHighest,
                    ),
                    Icon(
                      member.attendanceEnabled
                          ? Icons.location_on_outlined
                          : Icons.location_off_outlined,
                      color: member.attendanceEnabled
                          ? Theme.of(context).colorScheme.primary
                          : Theme.of(context).disabledColor,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _statusLabel(String status) => switch (status) {
    'active' => _ar ? 'نشط' : 'Active',
    'inactive' => _ar ? 'غير نشط' : 'Inactive',
    'pending' => _ar ? 'قيد الانتظار' : 'Pending',
    _ => _ar ? 'غير معروف' : 'Unknown',
  };

  String _roleLabel(String role) => switch (role) {
    'OWNER' => _ar ? 'مالك الشركة' : 'Owner',
    'MANAGER' || 'COMPANY_MANAGER' => _ar ? 'مدير' : 'Manager',
    'HR' || 'HR_OFFICER' => _ar ? 'الموارد البشرية' : 'HR officer',
    'SUPERVISOR' => _ar ? 'مشرف' : 'Supervisor',
    _ => _ar ? 'موظف' : 'Employee',
  };

  String _friendlyError(String? code, String? detail) => switch (code) {
    'invalid_session' =>
      _ar
          ? 'انتهت الجلسة. سجّل الدخول مرة أخرى.'
          : 'Your session expired. Sign in again.',
    'permission_denied' =>
      _ar
          ? 'ليست لديك صلاحية لعرض الموظفين.'
          : 'You do not have permission to view employees.',
    _ =>
      detail ??
          (_ar
              ? 'تعذر تحميل فريق الشركة.'
              : 'The company team could not be loaded.'),
  };
}
