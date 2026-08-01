import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/login_screen.dart';
import '../../features/home/presentation/role_workspace_screen.dart';
import '../../features/invitations/presentation/activate_invitation_screen.dart';
import '../../features/invitations/presentation/invitation_management_screen.dart';
import '../../features/splash/presentation/splash_screen.dart';

final GoRouter appRouter = GoRouter(
  routes: <RouteBase>[
    GoRoute(path: '/', builder: (context, state) => const SplashScreen()),
    GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
    GoRoute(
      path: '/activate-invitation',
      builder: (context, state) => const ActivateInvitationScreen(),
    ),
    GoRoute(
      path: '/app',
      builder: (context, state) => const RoleWorkspaceScreen(),
    ),
    GoRoute(
      path: '/app/invitations',
      builder: (context, state) => const InvitationManagementScreen(),
    ),
  ],
);
