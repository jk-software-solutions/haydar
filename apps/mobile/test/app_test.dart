import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haydar/app/haydar_app.dart';
import 'package:haydar/core/network/api_health.dart';

Widget buildTestApp() {
  return ProviderScope(
    overrides: <Override>[
      apiHealthProvider.overrideWith((ref) async => const ApiHealth.ready()),
    ],
    child: const HaydarApp(),
  );
}

void main() {
  testWidgets('starts Arabic-first with correct RTL direction', (tester) async {
    await tester.pumpWidget(buildTestApp());
    await tester.pump();
    await tester.pump();

    expect(find.text('HADIR | حاضر'), findsOneWidget);
    expect(find.text('حضور أوضح، وإدارة أسهل'), findsOneWidget);
    expect(find.text('الواجهة الأساسية جاهزة'), findsOneWidget);
    expect(find.text('الاتصال المحلي وقاعدة البيانات جاهزان'), findsOneWidget);
    expect(find.text('المتابعة لتسجيل الدخول'), findsOneWidget);
    expect(
      Directionality.of(tester.element(find.text('HADIR | حاضر'))),
      TextDirection.rtl,
    );
  });

  testWidgets('switches the same application shell to English LTR', (
    tester,
  ) async {
    await tester.pumpWidget(buildTestApp());
    await tester.pump();
    await tester.pump();

    await tester.tap(find.text('English'));
    await tester.pump();

    expect(find.text('Attendance, clearly managed'), findsOneWidget);
    expect(find.text('Local API and database are reachable'), findsOneWidget);
    expect(find.text('Continue to login'), findsOneWidget);
    expect(
      Directionality.of(tester.element(find.text('HADIR | حاضر'))),
      TextDirection.ltr,
    );
  });

  testWidgets('navigates to the real login form after local API is ready', (
    tester,
  ) async {
    await tester.pumpWidget(buildTestApp());
    await tester.pump();
    await tester.pump();

    await tester.tap(find.text('المتابعة لتسجيل الدخول'));
    await tester.pumpAndSettle();

    expect(find.text('تسجيل الدخول'), findsWidgets);
    expect(find.text('البريد الإلكتروني'), findsOneWidget);
    expect(find.text('كلمة المرور'), findsOneWidget);
  });
}
