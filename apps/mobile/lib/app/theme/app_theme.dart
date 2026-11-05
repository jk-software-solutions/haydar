import 'package:flutter/material.dart';

abstract final class AppColors {
  static const background = Color(0xFFF7F9FB);
  static const surface = Color(0xFFFFFFFF);
  static const mutedSurface = Color(0xFFF1F5F9);
  static const border = Color(0xFFE2E8F0);
  static const heading = Color(0xFF0F172A);
  static const body = Color(0xFF475569);
  static const secondaryText = Color(0xFF64748B);
  static const emerald = Color(0xFF0F766E);
  static const deepEmerald = Color(0xFF115E59);
  static const accent = Color(0xFF14B8A6);
  static const blue = Color(0xFF2563EB);
  static const success = Color(0xFF16A34A);
  static const warning = Color(0xFFF59E0B);
  static const error = Color(0xFFDC2626);
}

abstract final class AppTheme {
  static ThemeData get light => _theme(Brightness.light);
  static ThemeData get dark => _theme(Brightness.dark);

  static ThemeData _theme(Brightness brightness) {
    final scheme =
        ColorScheme.fromSeed(
          seedColor: AppColors.emerald,
          brightness: brightness,
        ).copyWith(
          primary: brightness == Brightness.light
              ? AppColors.emerald
              : AppColors.accent,
          onPrimary: Colors.white,
          primaryContainer: brightness == Brightness.light
              ? const Color(0xFFD7F3EE)
              : const Color(0xFF164E49),
          onPrimaryContainer: brightness == Brightness.light
              ? AppColors.deepEmerald
              : Colors.white,
          secondary: brightness == Brightness.light
              ? AppColors.deepEmerald
              : AppColors.accent,
          tertiary: AppColors.warning,
          error: AppColors.error,
          surface: brightness == Brightness.light
              ? AppColors.surface
              : const Color(0xFF111827),
          surfaceContainerLowest: brightness == Brightness.light
              ? AppColors.surface
              : const Color(0xFF0B1220),
          surfaceContainerLow: brightness == Brightness.light
              ? AppColors.background
              : const Color(0xFF172033),
          surfaceContainer: brightness == Brightness.light
              ? AppColors.mutedSurface
              : const Color(0xFF1E293B),
          surfaceContainerHighest: brightness == Brightness.light
              ? AppColors.mutedSurface
              : const Color(0xFF334155),
          outline: brightness == Brightness.light
              ? AppColors.border
              : const Color(0xFF64748B),
          outlineVariant: brightness == Brightness.light
              ? AppColors.border
              : const Color(0xFF334155),
        );

    final isLight = brightness == Brightness.light;

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: isLight ? AppColors.background : scheme.surface,
      visualDensity: VisualDensity.standard,
      textTheme: TextTheme(
        headlineSmall: TextStyle(
          fontSize: 26,
          height: 1.2,
          fontWeight: FontWeight.w800,
          color: isLight ? AppColors.heading : scheme.onSurface,
        ),
        titleLarge: TextStyle(
          fontSize: 20,
          height: 1.25,
          fontWeight: FontWeight.w700,
          color: isLight ? AppColors.heading : scheme.onSurface,
        ),
        titleMedium: TextStyle(
          fontSize: 16,
          height: 1.3,
          fontWeight: FontWeight.w700,
          color: isLight ? AppColors.heading : scheme.onSurface,
        ),
        bodyLarge: TextStyle(
          fontSize: 16,
          height: 1.45,
          color: isLight ? AppColors.body : scheme.onSurface,
        ),
        bodyMedium: TextStyle(
          fontSize: 14,
          height: 1.4,
          color: isLight ? AppColors.body : scheme.onSurfaceVariant,
        ),
        bodySmall: TextStyle(
          fontSize: 12,
          height: 1.35,
          color: isLight ? AppColors.secondaryText : scheme.onSurfaceVariant,
        ),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: isLight ? AppColors.surface : scheme.surface,
        foregroundColor: isLight ? AppColors.heading : scheme.onSurface,
        elevation: 0,
        scrolledUnderElevation: 1,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: isLight ? AppColors.heading : scheme.onSurface,
          fontSize: 20,
          fontWeight: FontWeight.w700,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isLight ? AppColors.surface : scheme.surfaceContainerHighest,
        labelStyle: TextStyle(
          color: isLight ? AppColors.secondaryText : scheme.onSurfaceVariant,
        ),
        hintStyle: TextStyle(
          color: isLight ? AppColors.secondaryText : scheme.onSurfaceVariant,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.outlineVariant),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.outlineVariant),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.primary, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 15,
        ),
      ),
      cardTheme: CardThemeData(
        margin: const EdgeInsets.symmetric(vertical: 6),
        elevation: 0,
        color: isLight ? AppColors.surface : scheme.surfaceContainer,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: BorderSide(color: scheme.outlineVariant),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(48, 48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(48, 48),
          foregroundColor: scheme.primary,
          side: BorderSide(color: scheme.primary.withValues(alpha: .65)),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: isLight ? AppColors.surface : scheme.surface,
        indicatorColor: isLight
            ? const Color(0xFFD7F3EE)
            : scheme.primaryContainer,
        surfaceTintColor: Colors.transparent,
        elevation: 2,
        labelTextStyle: WidgetStatePropertyAll(
          TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: isLight ? AppColors.body : scheme.onSurfaceVariant,
          ),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: isLight ? AppColors.surface : scheme.surfaceContainer,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        titleTextStyle: TextStyle(
          color: isLight ? AppColors.heading : scheme.onSurface,
          fontSize: 20,
          fontWeight: FontWeight.w700,
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: isLight
            ? AppColors.heading
            : scheme.surfaceContainerHighest,
        contentTextStyle: TextStyle(
          color: isLight ? Colors.white : scheme.onSurface,
          fontSize: 14,
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: isLight
            ? AppColors.mutedSurface
            : scheme.surfaceContainerHighest,
        selectedColor: isLight
            ? const Color(0xFFD7F3EE)
            : scheme.primaryContainer,
        side: BorderSide.none,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
        labelStyle: TextStyle(
          color: isLight ? AppColors.body : scheme.onSurface,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
