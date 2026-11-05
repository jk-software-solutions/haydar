import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';

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

  String _roleLabel(String roleCode, bool ar) => switch (roleCode) {
    'EMPLOYEE' => ar ? 'موظف' : 'Employee',
    'SUPERVISOR' => ar ? 'مشرف' : 'Supervisor',
    'HR' || 'HR_OFFICER' => ar ? 'موارد بشرية' : 'HR officer',
    'MANAGER' || 'COMPANY_MANAGER' => ar ? 'مدير' : 'Manager',
    _ => ar ? 'عضو فريق' : 'Team member',
  };

  String _statusLabel(String status, bool ar) => switch (status) {
    'pending' => ar ? 'قيد الانتظار' : 'Pending',
    'accepted' || 'activated' => ar ? 'تم التفعيل' : 'Activated',
    'expired' => ar ? 'منتهية' : 'Expired',
    'revoked' => ar ? 'ملغاة' : 'Revoked',
    _ => ar ? 'غير محددة' : 'Unknown',
  };

  String _expiryLabel(DateTime? expiresAt, bool ar) {
    if (expiresAt == null) return '';
    final date = MaterialLocalizations.of(
      context,
    ).formatMediumDate(expiresAt.toLocal());
    return ar ? 'تنتهي في $date' : 'Expires $date';
  }

  Future<void> _showActivationToken(CreatedInvitation invitation) async {
    final ar = Localizations.localeOf(context).languageCode == 'ar';
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(AppLocalizations.of(context).activationTokenCreatedTitle),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(
              ar
                  ? 'انسخ هذا الكود وأرسله للموظف. تم إبطال أي كود قديم لهذه الدعوة.'
                  : 'Copy this code and send it to the employee. Any old code for this invitation is now invalid.',
            ),
            const SizedBox(height: 12),
            SelectableText(invitation.activationToken),
          ],
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () async {
              await Clipboard.setData(
                ClipboardData(text: invitation.activationToken),
              );
              if (!context.mounted) return;
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text(ar ? 'تم نسخ الكود' : 'Code copied')),
              );
            },
            child: Text(ar ? 'نسخ الكود' : 'Copy code'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(MaterialLocalizations.of(context).closeButtonLabel),
          ),
        ],
      ),
    );
  }

  Future<void> _resendCode(InvitationSummary invitation) async {
    try {
      final updated = await ref
          .read(invitationApiProvider)
          .resendCode(invitation.id);
      if (!mounted) return;
      await _showActivationToken(updated);
      await _load();
    } on Object catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_friendlyError(error))));
    }
  }

  Future<void> _openCreateDialog() async {
    final created = await showDialog<CreatedInvitation>(
      context: context,
      builder: (_) => const _CreateInvitationDialog(),
    );
    if (created == null || !mounted) return;
    await _showActivationToken(created);
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
                    final ar =
                        Localizations.localeOf(context).languageCode == 'ar';
                    final role = _roleLabel(invitation.roleCode, ar);
                    final status = _statusLabel(invitation.status, ar);
                    final expiry = _expiryLabel(invitation.expiresAt, ar);
                    return Card(
                      child: ListTile(
                        leading: const Icon(Icons.mail_outline_rounded),
                        title: Text(invitation.fullName),
                        subtitle: Text(
                          '${invitation.email}\n$role · $status${expiry.isEmpty ? '' : '\n$expiry'}',
                        ),
                        isThreeLine: expiry.isNotEmpty,
                        trailing: invitation.status == 'pending'
                            ? IconButton.filledTonal(
                                tooltip:
                                    Localizations.localeOf(
                                          context,
                                        ).languageCode ==
                                        'ar'
                                    ? 'إنشاء ونسخ كود جديد'
                                    : 'Generate and copy a new code',
                                onPressed: () => _resendCode(invitation),
                                icon: const Icon(Icons.refresh_rounded),
                              )
                            : Chip(label: Text(status)),
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
