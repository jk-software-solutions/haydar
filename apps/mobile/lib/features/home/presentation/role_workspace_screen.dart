import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../auth/application/auth_api.dart';
import '../../auth/application/auth_controller.dart';

class RoleWorkspaceScreen extends ConsumerWidget {
  const RoleWorkspaceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final authState = ref.watch(authControllerProvider);
    final session = authState.session;

    if (authState.isInitializing) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (session == null) {
      return Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                const Icon(Icons.lock_outline_rounded, size: 48),
                const SizedBox(height: 16),
                Text(l10n.sessionRequired, textAlign: TextAlign.center),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: () => context.go('/login'),
                  child: Text(l10n.loginButton),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final primaryRole = session.roles.isEmpty
        ? 'EMPLOYEE'
        : session.roles.first;
    return Scaffold(
      appBar: AppBar(
        title: Text(_workspaceTitle(l10n, primaryRole)),
        actions: <Widget>[
          IconButton(
            tooltip: l10n.logoutButton,
            onPressed: authState.isSubmitting
                ? null
                : () => _signOut(context, ref),
            icon: const Icon(Icons.logout_rounded),
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: <Widget>[
            Text(
              l10n.welcomeUser(session.fullName),
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            Text(
              l10n.authenticatedWorkspaceDescription,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 24),
            _SessionCard(
              session: session,
              roleLabel: _roleLabel(l10n, primaryRole),
            ),
            const SizedBox(height: 16),
            Card(
              child: ListTile(
                leading: const Icon(Icons.verified_user_outlined),
                title: Text(l10n.secureSessionTitle),
                subtitle: Text(l10n.secureSessionDescription),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _signOut(BuildContext context, WidgetRef ref) async {
    try {
      await ref.read(authControllerProvider.notifier).signOut();
      if (context.mounted) {
        context.go('/login');
      }
    } on Object {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context).logoutError)),
        );
      }
    }
  }

  String _workspaceTitle(AppLocalizations l10n, String role) {
    return switch (role) {
      'OWNER' => l10n.ownerWorkspaceTitle,
      'MANAGER' || 'COMPANY_MANAGER' => l10n.managerWorkspaceTitle,
      'SUPERVISOR' => l10n.supervisorWorkspaceTitle,
      'HR' || 'HR_OFFICER' => l10n.hrWorkspaceTitle,
      _ => l10n.employeeWorkspaceTitle,
    };
  }

  String _roleLabel(AppLocalizations l10n, String role) {
    return switch (role) {
      'OWNER' => l10n.ownerRole,
      'MANAGER' || 'COMPANY_MANAGER' => l10n.managerRole,
      'SUPERVISOR' => l10n.supervisorRole,
      'HR' || 'HR_OFFICER' => l10n.hrRole,
      _ => l10n.employeeRole,
    };
  }
}

class _SessionCard extends StatelessWidget {
  const _SessionCard({required this.session, required this.roleLabel});

  final AuthSession session;
  final String roleLabel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            _SessionRow(
              icon: Icons.business_outlined,
              label: l10n.companyLabel,
              value: session.companyName,
            ),
            const Divider(height: 28),
            _SessionRow(
              icon: Icons.badge_outlined,
              label: l10n.roleLabel,
              value: roleLabel,
            ),
            const Divider(height: 28),
            _SessionRow(
              icon: Icons.alternate_email_rounded,
              label: l10n.emailLabel,
              value: session.email,
            ),
          ],
        ),
      ),
    );
  }
}

class _SessionRow extends StatelessWidget {
  const _SessionRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Icon(icon),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(label, style: Theme.of(context).textTheme.labelLarge),
              const SizedBox(height: 4),
              Text(value, style: Theme.of(context).textTheme.titleMedium),
            ],
          ),
        ),
      ],
    );
  }
}
