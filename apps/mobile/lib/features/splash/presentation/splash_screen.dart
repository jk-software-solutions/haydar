import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/localization/locale_controller.dart';
import '../../../app/theme/app_theme.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_health.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../auth/application/auth_controller.dart';

class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final textTheme = Theme.of(context).textTheme;
    final apiHealth = ref.watch(apiHealthProvider);
    final authState = ref.watch(authControllerProvider);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: <Widget>[
                  const _BrandMark(),
                  const SizedBox(height: 24),
                  Text(
                    '${l10n.appName} | ${l10n.appNameArabic}',
                    textAlign: TextAlign.center,
                    style: textTheme.headlineMedium?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    l10n.foundationMessage,
                    textAlign: TextAlign.center,
                    style: textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    l10n.foundationDescription,
                    textAlign: TextAlign.center,
                    style: textTheme.bodyLarge,
                  ),
                  const SizedBox(height: 24),
                  Semantics(
                    liveRegion: true,
                    child: Column(
                      children: <Widget>[
                        Chip(
                          avatar: Icon(
                            Icons.check_circle_outline_rounded,
                            color: Theme.of(context).colorScheme.primary,
                          ),
                          label: Text(l10n.foundationStatus),
                        ),
                        const SizedBox(height: 8),
                        _ApiStatusChip(apiHealth: apiHealth),
                        const SizedBox(height: 8),
                        if (!kReleaseMode)
                          Text(
                            '${l10n.apiEndpoint}: $apiBaseUrl',
                            textAlign: TextAlign.center,
                            style: textTheme.bodySmall,
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                  apiHealth.maybeWhen(
                    data: (_) => FilledButton.icon(
                      onPressed: authState.isInitializing
                          ? null
                          : () => context.go(
                              authState.session == null ? '/login' : '/app',
                            ),
                      icon: Icon(
                        authState.session == null
                            ? Icons.login_rounded
                            : Icons.dashboard_outlined,
                      ),
                      label: Text(
                        authState.session == null
                            ? l10n.continueToLogin
                            : l10n.openWorkspace,
                      ),
                    ),
                    orElse: () => OutlinedButton.icon(
                      onPressed: null,
                      icon: const Icon(Icons.login_rounded),
                      label: Text(l10n.continueToLogin),
                    ),
                  ),
                  const SizedBox(height: 16),
                  SegmentedButton<String>(
                    segments: <ButtonSegment<String>>[
                      ButtonSegment<String>(
                        value: 'ar',
                        label: Text(l10n.arabicLanguage),
                      ),
                      ButtonSegment<String>(
                        value: 'en',
                        label: Text(l10n.englishLanguage),
                      ),
                    ],
                    selected: <String>{
                      Localizations.localeOf(context).languageCode,
                    },
                    onSelectionChanged: (selection) {
                      ref
                          .read(localeControllerProvider.notifier)
                          .select(Locale(selection.single));
                    },
                  ),
                  const SizedBox(height: 20),
                  Image.asset(
                    'assets/branding/jk_main_logo.png',
                    width: 112,
                    semanticLabel: 'JK Software Solutions',
                  ),
                  const SizedBox(height: 4),
                  Text(
                    Localizations.localeOf(context).languageCode == 'ar'
                        ? 'تطوير JK Software Solutions'
                        : 'Developed by JK Software Solutions',
                    style: textTheme.labelSmall,
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ApiStatusChip extends StatelessWidget {
  const _ApiStatusChip({required this.apiHealth});

  final AsyncValue<ApiHealth> apiHealth;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;

    return apiHealth.when(
      loading: () => Chip(
        avatar: SizedBox.square(
          dimension: 18,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            color: colorScheme.primary,
          ),
        ),
        label: Text(l10n.apiChecking),
      ),
      error: (_, _) => Chip(
        avatar: Icon(Icons.cloud_off_outlined, color: colorScheme.error),
        label: Text(l10n.apiUnavailable),
      ),
      data: (_) => Chip(
        avatar: Icon(Icons.cloud_done_outlined, color: colorScheme.primary),
        label: Text(l10n.apiReady),
      ),
    );
  }
}

class _BrandMark extends StatelessWidget {
  const _BrandMark();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: <Color>[AppColors.deepEmerald, AppColors.emerald],
        ),
        borderRadius: BorderRadius.circular(24),
      ),
      child: const SizedBox.square(
        dimension: 88,
        child: Icon(Icons.fingerprint_rounded, color: Colors.white, size: 48),
      ),
    );
  }
}
