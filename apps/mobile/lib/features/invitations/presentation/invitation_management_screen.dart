import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../auth/application/auth_controller.dart';
import '../application/invitation_api.dart';

bool _canManageInvitations(List<String> roles) {
  return roles.any(
    (role) =>
        role == 'OWNER' ||
        role == 'MANAGER' ||
        role == 'COMPANY_MANAGER' ||
        role == 'HR' ||
        role == 'HR_OFFICER',
  );
}

class InvitationManagementScreen extends ConsumerStatefulWidget {
  const InvitationManagementScreen({super.key});

  @override
  ConsumerState<InvitationManagementScreen> createState() =>
      _InvitationManagementScreenState();
}

class _InvitationManagementScreenState
    extends ConsumerState<InvitationManagementScreen> {
  List<InvitationSummary> _items = const <InvitationSummary>[];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    final roles = ref.read(authControllerProvider).session?.roles ?? <String>[];
    if (_canManageInvitations(roles)) {
      Future<void>.microtask(_load);
    } else {
      _loading = false;
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await ref.read(invitationApiProvider).list();
      if (mounted) setState(() => _items = items);
    } on Object catch (error) {
      if (mounted) setState(() => _error = _friendlyError(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _friendlyError(Object error) {
    if (error is DioException && error.response?.data is Map<String, dynamic>) {
      final detail = (error.response!.data as Map<String, dynamic>)['detail'];
      if (detail is String) return detail;
    }
    return AppLocalizations.of(context).invitationLoadError;
  }

  Future<void> _openCreateDialog() async {
    final created = await showDialog<CreatedInvitation>(
      context: context,
      builder: (_) => const _CreateInvitationDialog(),
    );
    if (created == null || !mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(AppLocalizations.of(context).activationTokenCreatedTitle),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(
              AppLocalizations.of(context).activationTokenCreatedDescription,
            ),
            const SizedBox(height: 12),
            SelectableText(created.activationToken),
          ],
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(MaterialLocalizations.of(context).closeButtonLabel),
          ),
        ],
      ),
    );
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final roles =
        ref.watch(authControllerProvider).session?.roles ?? <String>[];
    final canManage = _canManageInvitations(roles);
    if (!canManage) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.manageInvitationsTitle)),
        body: Center(child: Text(l10n.permissionDenied)),
      );
    }
    return Scaffold(
      appBar: AppBar(title: Text(l10n.manageInvitationsTitle)),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openCreateDialog,
        icon: const Icon(Icons.person_add_alt_1_outlined),
        label: Text(l10n.createInvitationButton),
      ),
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
            ? Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Text(_error!, textAlign: TextAlign.center),
                      const SizedBox(height: 12),
                      OutlinedButton(
                        onPressed: _load,
                        child: Text(l10n.retryButton),
                      ),
                    ],
                  ),
                ),
              )
            : _items.isEmpty
            ? Center(child: Text(l10n.noInvitations))
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
                  itemCount: _items.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final invitation = _items[index];
                    return Card(
                      child: ListTile(
                        leading: const Icon(Icons.mail_outline_rounded),
                        title: Text(invitation.fullName),
                        subtitle: Text(
                          '${invitation.email}\n${invitation.roleCode}',
                        ),
                        isThreeLine: true,
                        trailing: Chip(label: Text(invitation.status)),
                      ),
                    );
                  },
                ),
              ),
      ),
    );
  }
}

class _CreateInvitationDialog extends ConsumerStatefulWidget {
  const _CreateInvitationDialog();

  @override
  ConsumerState<_CreateInvitationDialog> createState() =>
      _CreateInvitationDialogState();
}

class _CreateInvitationDialogState
    extends ConsumerState<_CreateInvitationDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  String _role = 'EMPLOYEE';
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final created = await ref
          .read(invitationApiProvider)
          .create(
            email: _emailController.text.trim(),
            fullName: _nameController.text.trim(),
            roleCode: _role,
          );
      if (mounted) Navigator.of(context).pop(created);
    } on Object catch (error) {
      if (mounted) {
        setState(() {
          _submitting = false;
          _error =
              error is DioException &&
                  error.response?.data is Map<String, dynamic> &&
                  (error.response!.data as Map<String, dynamic>)['detail']
                      is String
              ? (error.response!.data as Map<String, dynamic>)['detail']
                    as String
              : AppLocalizations.of(context).invitationCreateError;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.createInvitationTitle),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              TextFormField(
                controller: _nameController,
                decoration: InputDecoration(labelText: l10n.fullNameLabel),
                validator: (value) => value == null || value.trim().length < 2
                    ? l10n.fullNameValidation
                    : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                decoration: InputDecoration(labelText: l10n.emailLabel),
                validator: (value) => value == null || !value.contains('@')
                    ? l10n.emailValidation
                    : null,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _role,
                decoration: InputDecoration(labelText: l10n.roleLabel),
                items: <DropdownMenuItem<String>>[
                  DropdownMenuItem(
                    value: 'EMPLOYEE',
                    child: Text(l10n.employeeRole),
                  ),
                  DropdownMenuItem(
                    value: 'SUPERVISOR',
                    child: Text(l10n.supervisorRole),
                  ),
                  DropdownMenuItem(
                    value: 'HR_OFFICER',
                    child: Text(l10n.hrRole),
                  ),
                  DropdownMenuItem(
                    value: 'MANAGER',
                    child: Text(l10n.managerRole),
                  ),
                ],
                onChanged: (value) => setState(() => _role = value ?? _role),
              ),
              if (_error != null) ...<Widget>[
                const SizedBox(height: 12),
                Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
            ],
          ),
        ),
      ),
      actions: <Widget>[
        TextButton(
          onPressed: _submitting ? null : () => Navigator.of(context).pop(),
          child: Text(MaterialLocalizations.of(context).cancelButtonLabel),
        ),
        FilledButton(
          onPressed: _submitting ? null : _submit,
          child: Text(l10n.createInvitationButton),
        ),
      ],
    );
  }
}
