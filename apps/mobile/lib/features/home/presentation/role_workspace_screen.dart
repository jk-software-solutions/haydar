import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../auth/application/auth_api.dart';
import '../../auth/application/auth_controller.dart';
import '../../devices/presentation/employee_device_gate.dart';

class RoleWorkspaceScreen extends ConsumerStatefulWidget {
  const RoleWorkspaceScreen({super.key});

  @override
  ConsumerState<RoleWorkspaceScreen> createState() =>
      _RoleWorkspaceScreenState();
}

class _RoleWorkspaceScreenState extends ConsumerState<RoleWorkspaceScreen> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
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
    final employeeExperience = primaryRole == 'EMPLOYEE';
    final destinations = employeeExperience
        ? _employeeDestinations(l10n)
        : _managerDestinations(l10n);
    final selectedIndex = _selectedIndex
        .clamp(0, destinations.length - 1)
        .toInt();
    final workspace = Scaffold(
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
        child: _workspaceBody(
          l10n: l10n,
          session: session,
          role: primaryRole,
          employeeExperience: employeeExperience,
          selectedIndex: selectedIndex,
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: selectedIndex,
        onDestinationSelected: (index) =>
            setState(() => _selectedIndex = index),
        destinations: destinations,
      ),
    );
    return employeeExperience
        ? EmployeeDeviceGate(child: workspace)
        : workspace;
  }

  List<NavigationDestination> _employeeDestinations(AppLocalizations l10n) {
    return <NavigationDestination>[
      NavigationDestination(
        icon: const Icon(Icons.home_outlined),
        selectedIcon: const Icon(Icons.home_rounded),
        label: l10n.navHome,
      ),
      NavigationDestination(
        icon: const Icon(Icons.fingerprint_outlined),
        selectedIcon: const Icon(Icons.fingerprint_rounded),
        label: l10n.navAttendance,
      ),
      NavigationDestination(
        icon: const Icon(Icons.task_alt_outlined),
        selectedIcon: const Icon(Icons.task_alt_rounded),
        label: l10n.navTasks,
      ),
      NavigationDestination(
        icon: const Icon(Icons.assignment_outlined),
        selectedIcon: const Icon(Icons.assignment_rounded),
        label: l10n.navRequests,
      ),
      NavigationDestination(
        icon: const Icon(Icons.person_outline_rounded),
        selectedIcon: const Icon(Icons.person_rounded),
        label: l10n.navProfile,
      ),
    ];
  }

  List<NavigationDestination> _managerDestinations(AppLocalizations l10n) {
    return <NavigationDestination>[
      NavigationDestination(
        icon: const Icon(Icons.dashboard_outlined),
        selectedIcon: const Icon(Icons.dashboard_rounded),
        label: l10n.navDashboard,
      ),
      NavigationDestination(
        icon: const Icon(Icons.groups_outlined),
        selectedIcon: const Icon(Icons.groups_rounded),
        label: l10n.navTeam,
      ),
      NavigationDestination(
        icon: const Icon(Icons.fingerprint_outlined),
        selectedIcon: const Icon(Icons.fingerprint_rounded),
        label: l10n.navAttendance,
      ),
      NavigationDestination(
        icon: const Icon(Icons.task_alt_outlined),
        selectedIcon: const Icon(Icons.task_alt_rounded),
        label: l10n.navTasks,
      ),
      NavigationDestination(
        icon: const Icon(Icons.more_horiz_rounded),
        label: l10n.navMore,
      ),
    ];
  }

  Widget _workspaceBody({
    required AppLocalizations l10n,
    required AuthSession session,
    required String role,
    required bool employeeExperience,
    required int selectedIndex,
  }) {
    if (selectedIndex == 0) {
      return _DashboardView(
        session: session,
        roleLabel: _roleLabel(l10n, role),
      );
    }
    if (employeeExperience && selectedIndex == 4) {
      return _ProfileView(session: session, roleLabel: _roleLabel(l10n, role));
    }
    if (!employeeExperience && selectedIndex == 4) {
      return _ManagementMoreView(
        canManage: _canManageInvitations(role),
        onInvitations: () => context.push('/app/invitations'),
        onDevices: () => context.push('/app/device-requests'),
      );
    }
    final title = employeeExperience
        ? <String>[
            l10n.navHome,
            l10n.navAttendance,
            l10n.navTasks,
            l10n.navRequests,
            l10n.navProfile,
          ][selectedIndex]
        : <String>[
            l10n.navDashboard,
            l10n.navTeam,
            l10n.navAttendance,
            l10n.navTasks,
            l10n.navMore,
          ][selectedIndex];
    return _ScheduledFeatureView(title: title);
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

  bool _canManageInvitations(String role) {
    return role == 'OWNER' ||
        role == 'MANAGER' ||
        role == 'COMPANY_MANAGER' ||
        role == 'HR' ||
        role == 'HR_OFFICER';
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

class _DashboardView extends StatelessWidget {
  const _DashboardView({required this.session, required this.roleLabel});

  final AuthSession session;
  final String roleLabel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ListView(
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
        _SessionCard(session: session, roleLabel: roleLabel),
        const SizedBox(height: 16),
        Card(
          child: ListTile(
            leading: const Icon(Icons.verified_user_outlined),
            title: Text(l10n.secureSessionTitle),
            subtitle: Text(l10n.secureSessionDescription),
          ),
        ),
      ],
    );
  }
}

class _ProfileView extends StatelessWidget {
  const _ProfileView({required this.session, required this.roleLabel});

  final AuthSession session;
  final String roleLabel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ListView(
      padding: const EdgeInsets.all(24),
      children: <Widget>[
        Text(l10n.navProfile, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 16),
        _SessionCard(session: session, roleLabel: roleLabel),
      ],
    );
  }
}

class _ManagementMoreView extends StatelessWidget {
  const _ManagementMoreView({
    required this.canManage,
    required this.onInvitations,
    required this.onDevices,
  });

  final bool canManage;
  final VoidCallback onInvitations;
  final VoidCallback onDevices;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (!canManage) {
      return Center(child: Text(l10n.permissionDenied));
    }
    return ListView(
      padding: const EdgeInsets.all(24),
      children: <Widget>[
        Text(l10n.navMore, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 16),
        Card(
          child: ListTile(
            leading: const Icon(Icons.mark_email_unread_outlined),
            title: Text(l10n.manageInvitationsTitle),
            subtitle: Text(l10n.manageInvitationsDescription),
            trailing: const Icon(Icons.chevron_right_rounded),
            onTap: onInvitations,
          ),
        ),
        Card(
          child: ListTile(
            leading: const Icon(Icons.phonelink_lock_outlined),
            title: Text(l10n.deviceRequestsTitle),
            subtitle: Text(l10n.deviceRequestsDescription),
            trailing: const Icon(Icons.chevron_right_rounded),
            onTap: onDevices,
          ),
        ),
      ],
    );
  }
}

class _ScheduledFeatureView extends StatelessWidget {
  const _ScheduledFeatureView({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            const Icon(Icons.construction_rounded, size: 52),
            const SizedBox(height: 16),
            Text(title, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 8),
            Text(l10n.featureScheduledDescription, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
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
