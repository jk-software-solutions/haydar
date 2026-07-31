import 'package:flutter/material.dart';

abstract final class AppColors {
  static const emerald = Color(0xFF006B5E);
  static const deepEmerald = Color(0xFF004D43);
  static const blue = Color(0xFF2563EB);
  static const warning = Color(0xFFF59E0B);
  static const surface = Color(0xFFF6F8F7);
}

abstract final class AppTheme {
  static ThemeData get light => _theme(Brightness.light);
  static ThemeData get dark => _theme(Brightness.dark);

  static ThemeData _theme(Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.emerald,
      brightness: brightness,
      primary: AppColors.emerald,
      secondary: AppColors.blue,
      tertiary: AppColors.warning,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: brightness == Brightness.light
          ? AppColors.surface
          : scheme.surface,
      visualDensity: VisualDensity.standard,
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(48, 48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
    );
  }
}
