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
              ? data['detail'] as String? ?? '$error'
              : '$error',
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
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
            _ar ? 'فريق الشركة' : 'Company team',
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
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
                child: Text(_ar ? 'لا يوجد موظفون.' : 'No employees found.'),
              ),
            ),
          ..._members.map(
            (member) => Card(
              child: ListTile(
                leading: CircleAvatar(
                  child: Text(
                    member.name.isEmpty ? '?' : member.name.characters.first,
                  ),
                ),
                title: Text(member.name),
                subtitle: Text(
                  '${member.jobTitle ?? member.role}\n${member.email}',
                ),
                isThreeLine: true,
                trailing: Icon(
                  member.attendanceEnabled
                      ? Icons.location_on_outlined
                      : Icons.location_off_outlined,
                  color: member.status == 'active'
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(context).disabledColor,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
