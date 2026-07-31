import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/localization/locale_controller.dart';
import '../../../app/theme/app_theme.dart';
import '../../../l10n/generated/app_localizations.dart';

class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final textTheme = Theme.of(context).textTheme;

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
                    child: Chip(
                      avatar: Icon(
                        Icons.check_circle_outline_rounded,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                      label: Text(l10n.foundationStatus),
                    ),
                  ),
                  const SizedBox(height: 24),
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
                ],
              ),
            ),
          ),
        ),
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
