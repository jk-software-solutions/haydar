import 'package:flutter/material.dart';
import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:file_selector/file_selector.dart';
import 'package:dio/dio.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../../app/localization/locale_controller.dart';
import '../../../core/network/api_client.dart';
import '../../../core/notifications/push_notification_service.dart';
import '../../../core/widgets/jk_attribution.dart';
import '../../auth/application/auth_api.dart';
import '../../auth/application/auth_controller.dart';
import '../../attendance/presentation/attendance_screen.dart';
import '../../devices/presentation/employee_device_gate.dart';
import '../../notifications/presentation/notification_screen.dart';
import '../../notifications/application/notification_api.dart';
import '../../organization/presentation/admin_web_portal_screen.dart';
import '../../organization/application/employee_profile_api.dart';
import '../../organization/presentation/branch_shift_admin_screen.dart';
import '../../organization/presentation/group_management_screen.dart';
import '../../organization/presentation/owner_access_screen.dart';
import '../../requests/presentation/manager_approvals_screen.dart';
import '../../requests/presentation/requests_screen.dart';
import '../../requests/application/request_api.dart';
import '../../subscription/presentation/subscription_screen.dart';
import '../../tasks/application/task_api.dart';
import '../../tasks/presentation/tasks_screen.dart';
import '../../team/presentation/team_screen.dart';

class RoleWorkspaceScreen extends ConsumerStatefulWidget {
  const RoleWorkspaceScreen({super.key});

  @override
  ConsumerState<RoleWorkspaceScreen> createState() =>
      _RoleWorkspaceScreenState();
}

class _RoleWorkspaceScreenState extends ConsumerState<RoleWorkspaceScreen>
    with WidgetsBindingObserver {
  int _selectedIndex = 0;
  int _unreadNotifications = 0;
  int _taskBadgeCount = 0;
  int _requestBadgeCount = 0;
  Timer? _notificationTimer;
  late final PushNotificationService _pushService;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _pushService = PushNotificationService(
      ref.read(notificationApiProvider),
      onNotification: () => unawaited(_pollNotifications()),
    );
    _notificationTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _pollNotifications(),
    );
    _pollNotifications();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _notificationTimer?.cancel();
    unawaited(_pushService.dispose());
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      unawaited(_pollNotifications());
    }
  }

  Future<void> _pollNotifications() async {
    final session = ref.read(authControllerProvider).session;
    if (session == null) return;
    unawaited(_pushService.register(session));
    try {
      final count = await ref
          .read(notificationApiProvider)
          .unreadCount(session);
      if (mounted && count != _unreadNotifications) {
        final increased =
            _unreadNotifications > 0 && count > _unreadNotifications;
        setState(() => _unreadNotifications = count);
        if (increased) unawaited(_pushService.playNotificationSound());
      }
    } on Object catch (_) {
      // Notification polling is best-effort and must not interrupt attendance.
    }
    await _refreshBadgeCounts(session);
  }

  Future<void> _refreshBadgeCounts(AuthSession session) async {
    final manager = _primaryRole(session.roles) != 'EMPLOYEE';
    var taskCount = _taskBadgeCount;
    var requestCount = _requestBadgeCount;
    try {
      final tasks = await ref
          .read(taskApiProvider)
          .list(session, allCompany: manager);
      taskCount = tasks
          .where(
            (task) =>
                manager ? task.status != 'completed' : task.status == 'new',
          )
          .length;
    } on Object catch (_) {
      // Keep the last known task badge when a secondary request is unavailable.
    }
    try {
      final permissionRequests = await ref
          .read(requestApiProvider)
          .permissions(session, allCompany: manager);
      final leaveRequests = await ref
          .read(requestApiProvider)
          .leaves(session, allCompany: manager);
      requestCount = <RequestItem>[
        ...permissionRequests,
        ...leaveRequests,
      ].where((item) => item.status == 'pending').length;
    } on Object catch (_) {
      // Keep the last known request badge when a secondary request is unavailable.
    }
    if (mounted &&
        (taskCount != _taskBadgeCount || requestCount != _requestBadgeCount)) {
      setState(() {
        _taskBadgeCount = taskCount;
        _requestBadgeCount = requestCount;
      });
    }
  }

  Widget _badgeIcon(Widget icon, int count) {
    if (count <= 0) return icon;
    return Stack(
      clipBehavior: Clip.none,
      children: <Widget>[
        icon,
        PositionedDirectional(
          top: -8,
          end: -10,
          child: Container(
            constraints: const BoxConstraints(minWidth: 18, minHeight: 18),
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primary,
              borderRadius: BorderRadius.circular(99),
              border: Border.all(
                color: Theme.of(context).colorScheme.surface,
                width: 1.5,
              ),
            ),
            child: Text(
              count > 99 ? '99+' : '$count',
              style: TextStyle(
                color: Theme.of(context).colorScheme.onPrimary,
                fontSize: 10,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _openWhatsApp() async {
    final ar = Localizations.localeOf(context).languageCode == 'ar';
    final message = ar
        ? 'مرحباً، أحتاج إلى مساعدة في تطبيق دوام تك.'
        : 'Hello, I need help with DawamTech.';
    final uri = Uri.https('wa.me', '/966558005545', {'text': message});
    if (await launchUrl(uri, mode: LaunchMode.externalApplication)) return;
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          ar
              ? 'تعذر فتح واتساب. اتصل على +966 55 800 5545.'
              : 'Could not open WhatsApp. Call +966 55 800 5545.',
        ),
      ),
    );
  }

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

    final primaryRole = _primaryRole(session.roles);
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
            tooltip: Localizations.localeOf(context).languageCode == 'ar'
                ? 'English'
                : 'العربية',
            onPressed: () {
              final current = Localizations.localeOf(context).languageCode;
              ref
                  .read(localeControllerProvider.notifier)
                  .select(Locale(current == 'ar' ? 'en' : 'ar'));
            },
            icon: const Icon(Icons.translate_rounded),
          ),
          IconButton(
            tooltip: 'Notifications',
            onPressed: () async {
              await Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => NotificationScreen(
                    session: session,
                    onOpenDeepLink: (link) => _openNotificationLink(
                      link,
                      employeeExperience,
                      session,
                    ),
                  ),
                ),
              );
              _pollNotifications();
            },
            icon: _badgeIcon(
              const Icon(Icons.notifications_outlined),
              _unreadNotifications,
            ),
          ),
          IconButton(
            tooltip: Localizations.localeOf(context).languageCode == 'ar'
                ? 'التواصل مع دعم واتساب'
                : 'Contact WhatsApp support',
            onPressed: _openWhatsApp,
            icon: const Icon(Icons.chat_rounded),
            color: Colors.green,
          ),
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
          taskBadgeCount: _taskBadgeCount,
          requestBadgeCount: _requestBadgeCount,
          selectedIndex: selectedIndex,
        ),
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            NavigationBar(
              selectedIndex: selectedIndex,
              onDestinationSelected: (index) =>
                  setState(() => _selectedIndex = index),
              destinations: destinations,
            ),
            const Padding(
              padding: EdgeInsets.only(bottom: 4),
              child: JkAttribution(compact: true),
            ),
          ],
        ),
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
        icon: _badgeIcon(const Icon(Icons.task_alt_outlined), _taskBadgeCount),
        selectedIcon: _badgeIcon(
          const Icon(Icons.task_alt_rounded),
          _taskBadgeCount,
        ),
        label: l10n.navTasks,
      ),
      NavigationDestination(
        icon: _badgeIcon(
          const Icon(Icons.assignment_outlined),
          _requestBadgeCount,
        ),
        selectedIcon: _badgeIcon(
          const Icon(Icons.assignment_rounded),
          _requestBadgeCount,
        ),
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
        icon: _badgeIcon(const Icon(Icons.task_alt_outlined), _taskBadgeCount),
        selectedIcon: _badgeIcon(
          const Icon(Icons.task_alt_rounded),
          _taskBadgeCount,
        ),
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
    required int taskBadgeCount,
    required int requestBadgeCount,
    required int selectedIndex,
  }) {
    if (selectedIndex == 0) {
      return _DashboardView(
        session: session,
        roleLabel: _roleLabel(l10n, role),
        employeeExperience: employeeExperience,
        taskBadgeCount: taskBadgeCount,
        requestBadgeCount: requestBadgeCount,
        onOpenDestination: (index) => setState(() => _selectedIndex = index),
      );
    }
    if (employeeExperience && selectedIndex == 1) {
      return AttendanceScreen(session: session);
    }
    if (employeeExperience && selectedIndex == 2) {
      return TasksScreen(session: session);
    }
    if (employeeExperience && selectedIndex == 3) {
      return RequestsScreen(session: session);
    }
    if (!employeeExperience && selectedIndex == 2) {
      return session.can('attendance:view')
          ? AttendanceScreen(session: session, managerMode: true)
          : Center(child: Text(l10n.permissionDenied));
    }
    if (!employeeExperience && selectedIndex == 1) {
      return session.can('members:view')
          ? TeamScreen(session: session)
          : Center(child: Text(l10n.permissionDenied));
    }
    if (!employeeExperience && selectedIndex == 3) {
      return session.can('tasks:view')
          ? TasksScreen(session: session, managerMode: true)
          : Center(child: Text(l10n.permissionDenied));
    }
    if (employeeExperience && selectedIndex == 4) {
      return _ProfileView(session: session, roleLabel: _roleLabel(l10n, role));
    }
    if (!employeeExperience && selectedIndex == 4) {
      return _ManagementMoreView(
        canManageAccess: session.roles.contains('OWNER'),
        canManageGroups: session.can('departments:manage'),
        canManageInvitations: session.can('members:create'),
        canManageDevices: session.can('devices:manage'),
        canManageBranchShifts:
            session.can('branches:manage') || session.can('shifts:manage'),
        canOpenSiteControls: _canEnterSiteControls(session),
        canManageApprovals:
            session.can('permissions:manage') || session.can('leave:manage'),
        canManageSubscription:
            session.can('subscription:view') ||
            session.can('subscription:manage') ||
            session.roles.contains('OWNER'),
        onInvitations: () => context.push('/app/invitations'),
        onAccess: () => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => OwnerAccessScreen(session: session),
          ),
        ),
        onGroups: () => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => GroupManagementScreen(session: session),
          ),
        ),
        onBranchShifts: () => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => BranchShiftAdminScreen(
              session: session,
              canManageBranches: session.can('branches:manage'),
            ),
          ),
        ),
        onSiteControls: () => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => AdminWebPortalScreen(session: session),
          ),
        ),
        onDevices: () => context.push('/app/device-requests'),
        onApprovals: () => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => ManagerApprovalsScreen(session: session),
          ),
        ),
        onSubscription: () => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => SubscriptionScreen(session: session),
          ),
        ),
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

  void _openNotificationLink(
    String link,
    bool employeeExperience,
    AuthSession session,
  ) {
    if (link.startsWith('/app/tasks')) {
      setState(() => _selectedIndex = employeeExperience ? 2 : 3);
    } else if (link.startsWith('/app/attendance')) {
      setState(() => _selectedIndex = employeeExperience ? 1 : 2);
    } else if (link.startsWith('/app/requests')) {
      if (employeeExperience) {
        setState(() => _selectedIndex = 3);
      } else {
        Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => ManagerApprovalsScreen(session: session),
          ),
        );
      }
    }
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

  String _primaryRole(List<String> roles) {
    for (final role in const <String>[
      'OWNER',
      'MANAGER',
      'HR_OFFICER',
      'SUPERVISOR',
      'EMPLOYEE',
    ]) {
      if (roles.contains(role)) return role;
    }
    return 'EMPLOYEE';
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

  bool _canEnterSiteControls(AuthSession session) => session.roles.any(
    (role) => <String>{
      'OWNER',
      'MANAGER',
      'COMPANY_MANAGER',
      'HR_OFFICER',
      'SUPERVISOR',
    }.contains(role),
  );
}

class _DashboardView extends StatelessWidget {
  const _DashboardView({
    required this.session,
    required this.roleLabel,
    required this.employeeExperience,
    required this.taskBadgeCount,
    required this.requestBadgeCount,
    required this.onOpenDestination,
  });

  final AuthSession session;
  final String roleLabel;
  final bool employeeExperience;
  final int taskBadgeCount;
  final int requestBadgeCount;
  final ValueChanged<int> onOpenDestination;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ListView(
      padding: const EdgeInsets.all(24),
      children: <Widget>[
        Card(
          color: Theme.of(context).colorScheme.primaryContainer,
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              children: <Widget>[
                CircleAvatar(
                  radius: 28,
                  backgroundColor: Theme.of(context).colorScheme.primary,
                  foregroundColor: Theme.of(context).colorScheme.onPrimary,
                  child: Text(
                    session.fullName.isEmpty
                        ? '?'
                        : session.fullName.characters.first,
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        l10n.welcomeUser(session.fullName),
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 4),
                      Text(session.companyName),
                      const SizedBox(height: 8),
                      Chip(label: Text(roleLabel)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Text(
          _todayLabel(context),
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        if (employeeExperience) ...<Widget>[
          const SizedBox(height: 10),
          _EmployeeAssignmentSummary(session: session),
        ],
        const SizedBox(height: 20),
        Text(
          employeeExperience
              ? (Localizations.localeOf(context).languageCode == 'ar'
                    ? 'الوصول السريع'
                    : 'Quick actions')
              : (Localizations.localeOf(context).languageCode == 'ar'
                    ? 'إدارة العمل'
                    : 'Work management'),
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 8),
        ..._actions(context, l10n),
        const SizedBox(height: 14),
        Card(
          child: ExpansionTile(
            leading: const Icon(Icons.verified_user_outlined),
            title: Text(l10n.secureSessionTitle),
            subtitle: Text(l10n.secureSessionDescription),
            children: <Widget>[
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 18),
                child: _SessionCard(session: session, roleLabel: roleLabel),
              ),
            ],
          ),
        ),
      ],
    );
  }

  List<Widget> _actions(BuildContext context, AppLocalizations l10n) {
    final ar = Localizations.localeOf(context).languageCode == 'ar';
    final actions = employeeExperience
        ? <
            ({
              IconData icon,
              String title,
              String subtitle,
              int index,
              int count,
            })
          >[
            (
              icon: Icons.fingerprint_rounded,
              title: ar ? 'تسجيل الحضور' : 'Record attendance',
              subtitle: ar
                  ? 'سجّل حضورك وانصرافك'
                  : 'Record arrival and departure',
              index: 1,
              count: 0,
            ),
            (
              icon: Icons.task_alt_rounded,
              title: ar ? 'مهامي الحالية' : 'My current tasks',
              subtitle: ar
                  ? 'راجع المهام وحدّث حالتها'
                  : 'Review and update your tasks',
              index: 2,
              count: taskBadgeCount,
            ),
            (
              icon: Icons.assignment_rounded,
              title: ar ? 'طلباتي' : 'My requests',
              subtitle: ar
                  ? 'أرسل طلبًا أو تابع الموافقات'
                  : 'Send a request or follow approvals',
              index: 3,
              count: requestBadgeCount,
            ),
          ]
        : <
            ({
              IconData icon,
              String title,
              String subtitle,
              int index,
              int count,
            })
          >[
            if (session.can('members:view'))
              (
                icon: Icons.groups_rounded,
                title: ar ? 'فريق الشركة' : 'Company team',
                subtitle: ar ? 'عرض فريق الشركة' : 'View your company team',
                index: 1,
                count: 0,
              ),
            if (session.can('attendance:view'))
              (
                icon: Icons.fingerprint_rounded,
                title: ar ? 'متابعة الحضور' : 'Attendance overview',
                subtitle: ar ? 'متابعة الحضور والانصراف' : 'Monitor attendance',
                index: 2,
                count: 0,
              ),
            if (session.can('tasks:view'))
              (
                icon: Icons.task_alt_rounded,
                title: ar ? 'متابعة المهام' : 'Task follow-up',
                subtitle: ar ? 'متابعة المهام' : 'Follow up on tasks',
                index: 3,
                count: taskBadgeCount,
              ),
          ];
    return actions
        .map(
          (action) => Card(
            child: ListTile(
              minVerticalPadding: 14,
              leading: _DashboardBadgeIcon(
                icon: action.icon,
                count: action.count,
                color: Theme.of(context).colorScheme.primary,
              ),
              title: Text(action.title),
              subtitle: Text(action.subtitle),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => onOpenDestination(action.index),
            ),
          ),
        )
        .toList(growable: false);
  }

  String _todayLabel(BuildContext context) {
    final now = DateTime.now();
    final ar = Localizations.localeOf(context).languageCode == 'ar';
    final date = MaterialLocalizations.of(context).formatMediumDate(now);
    return ar ? 'اليوم: $date' : 'Today: $date';
  }
}

class _DashboardBadgeIcon extends StatelessWidget {
  const _DashboardBadgeIcon({
    required this.icon,
    required this.count,
    required this.color,
  });

  final IconData icon;
  final int count;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final iconWidget = Icon(icon, color: color);
    if (count <= 0) return iconWidget;
    return Stack(
      clipBehavior: Clip.none,
      children: <Widget>[
        iconWidget,
        PositionedDirectional(
          top: -9,
          end: -11,
          child: Container(
            constraints: const BoxConstraints(minWidth: 18, minHeight: 18),
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(99),
              border: Border.all(
                color: Theme.of(context).colorScheme.surface,
                width: 1.5,
              ),
            ),
            child: Text(
              count > 99 ? '99+' : '$count',
              style: TextStyle(
                color: Theme.of(context).colorScheme.onPrimary,
                fontSize: 10,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _ProfileView extends ConsumerStatefulWidget {
  const _ProfileView({required this.session, required this.roleLabel});

  final AuthSession session;
  final String roleLabel;

  @override
  ConsumerState<_ProfileView> createState() => _ProfileViewState();
}

class _ProfileViewState extends ConsumerState<_ProfileView> {
  EmployeeProfileData? _profile;
  List<EmployeeBranchAssignment> _branches = const <EmployeeBranchAssignment>[];
  List<EmployeeShiftAssignment> _shifts = const <EmployeeShiftAssignment>[];
  String? _error;
  bool _saving = false;

  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = ref.read(employeeProfileApiProvider);
      final values = await Future.wait<Object>(<Future<Object>>[
        api.me(widget.session),
        api.myBranches(widget.session),
        api.myShifts(widget.session),
      ]);
      if (!mounted) return;
      setState(() {
        _profile = values[0] as EmployeeProfileData;
        _branches = values[1] as List<EmployeeBranchAssignment>;
        _shifts = values[2] as List<EmployeeShiftAssignment>;
        _error = null;
      });
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    }
  }

  Future<void> _choosePhoto() async {
    if (_saving) return;
    try {
      const images = XTypeGroup(
        label: 'profile-photo',
        extensions: <String>['jpg', 'jpeg', 'png', 'webp'],
      );
      final file = await openFile(acceptedTypeGroups: <XTypeGroup>[images]);
      if (file == null) return;
      final bytes = await file.readAsBytes();
      setState(() => _saving = true);
      final api = ref.read(employeeProfileApiProvider);
      final fileId = await api.uploadImage(
        widget.session,
        filename: file.name,
        bytes: bytes,
      );
      if (fileId.isEmpty) {
        throw StateError('The server did not return the photo.');
      }
      final profile = await api.setAvatar(
        widget.session,
        version: _profile?.version ?? 1,
        fileId: fileId,
      );
      if (mounted) setState(() => _profile = profile);
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _removePhoto() async {
    final current = _profile;
    if (_saving || current == null || current.avatarFileId == null) return;
    setState(() => _saving = true);
    try {
      final profile = await ref
          .read(employeeProfileApiProvider)
          .setAvatar(widget.session, version: current.version, fileId: null);
      if (mounted) setState(() => _profile = profile);
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  String _fileUrl(String fileId) =>
      '${apiBaseUrl.replaceFirst(RegExp(r'/+$'), '')}/files/$fileId';

  String _assignmentPeriod(DateTime? from, DateTime? to) {
    final start = from == null ? '' : _formatDate(from);
    final end = to == null ? (_ar ? 'مفتوح' : 'Open-ended') : _formatDate(to);
    if (start.isEmpty) return end;
    return _ar ? 'من $start إلى $end' : '$start – $end';
  }

  String _formatDate(DateTime value) =>
      MaterialLocalizations.of(context).formatMediumDate(value.toLocal());

  String _timeLabel(String value) {
    if (value.length >= 5) return value.substring(0, 5);
    return value;
  }

  String _message(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map<String, dynamic>) {
        final detail = data['detail'];
        if (detail is String && detail.isNotEmpty) return detail;
      }
    }
    return _ar ? 'تعذر تحديث الملف الشخصي.' : 'Could not update the profile.';
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ListView(
      padding: const EdgeInsets.all(24),
      children: <Widget>[
        Text(l10n.navProfile, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 16),
        if (_error != null)
          Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(_error!, textAlign: TextAlign.center),
            ),
          ),
        if (_profile == null)
          const Center(child: CircularProgressIndicator())
        else ...[
          _ProfilePhotoCard(
            profile: _profile!,
            session: widget.session,
            imageUrl: _profile!.avatarFileId == null
                ? null
                : _fileUrl(_profile!.avatarFileId!),
            saving: _saving,
            arabic: _ar,
            onChoose: _choosePhoto,
            onRemove: _removePhoto,
          ),
          const SizedBox(height: 12),
          _SessionCard(session: widget.session, roleLabel: widget.roleLabel),
          const SizedBox(height: 12),
          _AssignmentCard(
            icon: Icons.store_mall_directory_outlined,
            title: _ar ? 'الفرع' : 'Branch',
            value: _branches.isEmpty
                ? (_ar ? 'لا يوجد فرع محدد' : 'No branch assigned')
                : _branches
                      .map(
                        (item) =>
                            '${item.name} · ${item.code}\n${_assignmentPeriod(item.effectiveFrom, item.effectiveTo)}',
                      )
                      .join('\n'),
          ),
          _AssignmentCard(
            icon: Icons.schedule_rounded,
            title: _ar ? 'الورديات' : 'Shifts',
            value: _shifts.isEmpty
                ? (_ar ? 'لا توجد وردية محددة' : 'No shift assigned')
                : _shifts
                      .map(
                        (item) =>
                            '${item.name} · ${item.code}\n${_timeLabel(item.startTime)} – ${_timeLabel(item.endTime)}\n${_assignmentPeriod(item.effectiveFrom, item.effectiveTo)}',
                      )
                      .join('\n'),
          ),
        ],
      ],
    );
  }
}

class _EmployeeAssignmentSummary extends ConsumerStatefulWidget {
  const _EmployeeAssignmentSummary({required this.session});

  final AuthSession session;

  @override
  ConsumerState<_EmployeeAssignmentSummary> createState() =>
      _EmployeeAssignmentSummaryState();
}

class _EmployeeAssignmentSummaryState
    extends ConsumerState<_EmployeeAssignmentSummary> {
  List<EmployeeBranchAssignment> _branches = const <EmployeeBranchAssignment>[];
  List<EmployeeShiftAssignment> _shifts = const <EmployeeShiftAssignment>[];
  bool _loading = true;

  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = ref.read(employeeProfileApiProvider);
      final values = await Future.wait<Object>(<Future<Object>>[
        api.myBranches(widget.session),
        api.myShifts(widget.session),
      ]);
      if (!mounted) return;
      setState(() {
        _branches = values[0] as List<EmployeeBranchAssignment>;
        _shifts = values[1] as List<EmployeeShiftAssignment>;
        _loading = false;
      });
    } on Object {
      if (mounted) setState(() => _loading = false);
    }
  }

  bool _effectiveToday(DateTime? from, DateTime? to) {
    final today = DateTime.now();
    final day = DateTime(today.year, today.month, today.day);
    final start = from == null
        ? null
        : DateTime(
            from.toLocal().year,
            from.toLocal().month,
            from.toLocal().day,
          );
    final end = to == null
        ? null
        : DateTime(to.toLocal().year, to.toLocal().month, to.toLocal().day);
    return (start == null || !day.isBefore(start)) &&
        (end == null || !day.isAfter(end));
  }

  String _period(DateTime? from, DateTime? to) {
    final start = from == null ? '' : _formatDate(from);
    final end = to == null ? (_ar ? 'مفتوح' : 'Open-ended') : _formatDate(to);
    if (start.isEmpty) return end;
    return _ar ? 'من $start إلى $end' : '$start – $end';
  }

  String _formatDate(DateTime value) =>
      MaterialLocalizations.of(context).formatMediumDate(value.toLocal());

  String _time(String value) =>
      value.length >= 5 ? value.substring(0, 5) : value;

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(16),
          child: LinearProgressIndicator(),
        ),
      );
    }
    final branch = _branches
        .where((item) => _effectiveToday(item.effectiveFrom, item.effectiveTo))
        .firstOrNull;
    final shift = _shifts
        .where((item) => _effectiveToday(item.effectiveFrom, item.effectiveTo))
        .firstOrNull;
    final date = MaterialLocalizations.of(
      context,
    ).formatMediumDate(DateTime.now());
    return Card(
      color: Theme.of(context).colorScheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(
              _ar ? 'تعيين اليوم · $date' : 'Today\'s assignment · $date',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 10),
            Row(
              children: <Widget>[
                const Icon(Icons.store_mall_directory_outlined),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    branch == null
                        ? (_ar
                              ? 'لا يوجد فرع معيّن اليوم'
                              : 'No branch assigned today')
                        : '${branch.name} · ${branch.code}\n${_period(branch.effectiveFrom, branch.effectiveTo)}',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: <Widget>[
                const Icon(Icons.schedule_rounded),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    shift == null
                        ? (_ar
                              ? 'لا توجد وردية معيّنة اليوم'
                              : 'No shift assigned today')
                        : '${shift.name} · ${shift.code}\n${_time(shift.startTime)} – ${_time(shift.endTime)}',
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfilePhotoCard extends StatelessWidget {
  const _ProfilePhotoCard({
    required this.profile,
    required this.session,
    required this.imageUrl,
    required this.saving,
    required this.arabic,
    required this.onChoose,
    required this.onRemove,
  });

  final EmployeeProfileData profile;
  final AuthSession session;
  final String? imageUrl;
  final bool saving;
  final bool arabic;
  final VoidCallback onChoose;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final image = imageUrl == null
        ? null
        : NetworkImage(
            imageUrl!,
            headers: <String, String>{
              'Authorization': 'Bearer ${session.accessToken}',
            },
          );
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: <Widget>[
            CircleAvatar(
              radius: 48,
              backgroundImage: image,
              child: image == null
                  ? Text(
                      profile.displayName.isEmpty
                          ? '?'
                          : profile.displayName.substring(0, 1).toUpperCase(),
                      style: Theme.of(context).textTheme.headlineMedium,
                    )
                  : null,
            ),
            const SizedBox(height: 12),
            Text(
              profile.displayName,
              style: Theme.of(context).textTheme.titleLarge,
              textAlign: TextAlign.center,
            ),
            if (profile.jobTitle != null && profile.jobTitle!.isNotEmpty)
              Text(profile.jobTitle!, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            Wrap(
              alignment: WrapAlignment.center,
              spacing: 8,
              children: <Widget>[
                FilledButton.icon(
                  onPressed: saving ? null : onChoose,
                  icon: const Icon(Icons.add_a_photo_outlined),
                  label: Text(
                    arabic ? 'إضافة صورة الموظف' : 'Add employee photo',
                  ),
                ),
                if (imageUrl != null)
                  TextButton(
                    onPressed: saving ? null : onRemove,
                    child: Text(arabic ? 'إزالة الصورة' : 'Remove photo'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _AssignmentCard extends StatelessWidget {
  const _AssignmentCard({
    required this.icon,
    required this.title,
    required this.value,
  });

  final IconData icon;
  final String title;
  final String value;

  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      leading: Icon(icon),
      title: Text(title),
      subtitle: Text(value),
    ),
  );
}

class _ManagementMoreView extends StatelessWidget {
  const _ManagementMoreView({
    required this.canManageAccess,
    required this.canManageGroups,
    required this.canManageInvitations,
    required this.canManageDevices,
    required this.canManageBranchShifts,
    required this.canOpenSiteControls,
    required this.canManageApprovals,
    required this.canManageSubscription,
    required this.onInvitations,
    required this.onAccess,
    required this.onGroups,
    required this.onBranchShifts,
    required this.onSiteControls,
    required this.onDevices,
    required this.onApprovals,
    required this.onSubscription,
  });

  final bool canManageAccess;
  final bool canManageGroups;
  final bool canManageInvitations;
  final bool canManageDevices;
  final bool canManageBranchShifts;
  final bool canOpenSiteControls;
  final bool canManageApprovals;
  final bool canManageSubscription;
  final VoidCallback onInvitations;
  final VoidCallback onAccess;
  final VoidCallback onGroups;
  final VoidCallback onBranchShifts;
  final VoidCallback onSiteControls;
  final VoidCallback onDevices;
  final VoidCallback onApprovals;
  final VoidCallback onSubscription;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (!canManageAccess &&
        !canManageGroups &&
        !canManageInvitations &&
        !canManageDevices &&
        !canManageBranchShifts &&
        !canOpenSiteControls &&
        !canManageApprovals &&
        !canManageSubscription) {
      return Center(child: Text(l10n.permissionDenied));
    }
    return ListView(
      padding: const EdgeInsets.all(24),
      children: <Widget>[
        Text(l10n.navMore, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 16),
        if (canOpenSiteControls)
          Card(
            child: ListTile(
              leading: const Icon(Icons.language_rounded),
              title: Text(
                Localizations.localeOf(context).languageCode == 'ar'
                    ? 'كل تحكمات الموقع'
                    : 'All site admin controls',
              ),
              subtitle: Text(
                Localizations.localeOf(context).languageCode == 'ar'
                    ? 'افتح بوابة إدارة الموقع كاملة داخل التطبيق.'
                    : 'Open the full web admin portal inside the app.',
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: onSiteControls,
            ),
          ),
        if (canManageSubscription)
          Card(
            child: ListTile(
              leading: const Icon(Icons.workspace_premium_outlined),
              title: Text(
                Localizations.localeOf(context).languageCode == 'ar'
                    ? 'الاشتراكات'
                    : 'Subscriptions',
              ),
              subtitle: Text(
                Localizations.localeOf(context).languageCode == 'ar'
                    ? 'عرض الباقات وإرسال طلب تفعيل اشتراك الشركة.'
                    : 'View plans and request activation for your company.',
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: onSubscription,
            ),
          ),
        if (canManageAccess)
          Card(
            child: ListTile(
              leading: const Icon(Icons.admin_panel_settings_outlined),
              title: Text(
                Localizations.localeOf(context).languageCode == 'ar'
                    ? 'الأدوار والصلاحيات'
                    : 'Roles and access',
              ),
              subtitle: Text(
                Localizations.localeOf(context).languageCode == 'ar'
                    ? 'إدارة أدوار الأعضاء وصلاحياتهم ونطاق عملهم.'
                    : 'Manage member roles, permission overrides, and scope.',
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: onAccess,
            ),
          ),
        if (canManageGroups)
          Card(
            child: ListTile(
              leading: const Icon(Icons.group_work_outlined),
              title: Text(
                Localizations.localeOf(context).languageCode == 'ar'
                    ? 'المجموعات التشغيلية'
                    : 'Operational groups',
              ),
              subtitle: Text(
                Localizations.localeOf(context).languageCode == 'ar'
                    ? 'إنشاء مجموعات العمل وتعيين أعضائها.'
                    : 'Create work groups and assign their members.',
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: onGroups,
            ),
          ),
        if (canManageBranchShifts)
          Card(
            child: ListTile(
              leading: const Icon(Icons.store_mall_directory_outlined),
              title: Text(
                Localizations.localeOf(context).languageCode == 'ar'
                    ? 'الإجراءات الإدارية'
                    : 'Administrative actions',
              ),
              subtitle: Text(
                Localizations.localeOf(context).languageCode == 'ar'
                    ? 'الفروع والورديات وشبكات Wi‑Fi من مكان واحد.'
                    : 'Manage branches, shifts, and Wi‑Fi from one place.',
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: onBranchShifts,
            ),
          ),
        if (canManageApprovals)
          Card(
            child: ListTile(
              leading: const Icon(Icons.approval_outlined),
              title: Text(
                Localizations.localeOf(context).languageCode == 'ar'
                    ? 'الموافقات'
                    : 'Approvals',
              ),
              subtitle: Text(
                Localizations.localeOf(context).languageCode == 'ar'
                    ? 'مراجعة الاستئذانات والإجازات.'
                    : 'Review permission and leave requests.',
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: onApprovals,
            ),
          ),
        if (canManageInvitations)
          Card(
            child: ListTile(
              leading: const Icon(Icons.mark_email_unread_outlined),
              title: Text(l10n.manageInvitationsTitle),
              subtitle: Text(l10n.manageInvitationsDescription),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: onInvitations,
            ),
          ),
        if (canManageDevices)
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
