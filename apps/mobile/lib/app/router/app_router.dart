import 'package:go_router/go_router.dart';

import '../../features/splash/presentation/splash_screen.dart';

final GoRouter appRouter = GoRouter(
  routes: <RouteBase>[
    GoRoute(path: '/', builder: (context, state) => const SplashScreen()),
  ],
);
