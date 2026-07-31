import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final localeControllerProvider =
    StateNotifierProvider<LocaleController, Locale>(
      (ref) => LocaleController(),
    );

class LocaleController extends StateNotifier<Locale> {
  LocaleController() : super(const Locale('ar'));

  void select(Locale locale) {
    if (locale.languageCode == 'ar' || locale.languageCode == 'en') {
      state = locale;
    }
  }
}
