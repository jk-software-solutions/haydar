import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haydar/app/haydar_app.dart';
import 'package:haydar/core/network/api_health.dart';
import 'package:haydar/features/auth/application/auth_api.dart';
import 'package:haydar/features/auth/application/auth_controller.dart';
import 'package:haydar/features/devices/application/device_api.dart';
import 'package:haydar/features/home/presentation/role_workspace_screen.dart';
import 'package:haydar/l10n/generated/app_localizations.dart';

Widget buildTestApp() {
  return ProviderScope(
    overrides: <Override>[
      apiHealthProvider.overrideWith((ref) async => const ApiHealth.ready()),
      authControllerProvider.overrideWith(
        (ref) => AuthController.forTest(const AuthState.signedOut()),
      ),
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

    await tester.tap(find.text('لدي رمز دعوة'));
    await tester.pumpAndSettle();
    expect(find.text('تفعيل الدعوة'), findsWidgets);
    expect(find.text('رمز الدعوة'), findsOneWidget);
  });

  testWidgets('shows the authenticated role workspace after login', (
    tester,
  ) async {
    const session = AuthSession(
      accessToken: 'placeholder-access-token',
      refreshToken: 'placeholder-refresh-token',
      userId: 'user-id',
      email: 'owner@example.com',
      companyId: 'company-id',
      membershipId: 'membership-id',
      companyName: 'My Company',
      fullName: 'Jawad Owner',
      roles: <String>['OWNER'],
      permissions: <String>[
        'members:view',
        'members:create',
        'devices:manage',
        'permissions:manage',
      ],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          authControllerProvider.overrideWith(
            (ref) =>
                AuthController.forTest(const AuthState.authenticated(session)),
          ),
          deviceBindingProvider.overrideWith(
            (ref) async => const DeviceBinding(
              status: 'approved',
              requiresApproval: false,
            ),
          ),
        ],
        child: const MaterialApp(
          locale: Locale('ar'),
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: <LocalizationsDelegate<dynamic>>[
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
          ],
          home: RoleWorkspaceScreen(),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('مساحة عمل مالك الشركة'), findsOneWidget);
    expect(find.text('مرحباً، Jawad Owner'), findsOneWidget);
    expect(find.text('My Company'), findsOneWidget);
    expect(find.text('مالك الشركة'), findsOneWidget);
    expect(find.text('لوحة التحكم'), findsOneWidget);
    expect(find.text('الفريق'), findsOneWidget);
    await tester.tap(find.text('المزيد'));
    await tester.pumpAndSettle();
    expect(find.text('دعوات الموظفين'), findsOneWidget);
    expect(find.text('طلبات تغيير الأجهزة'), findsOneWidget);
  });

  testWidgets('hides invitation management from an employee workspace', (
    tester,
  ) async {
    const session = AuthSession(
      accessToken: 'placeholder-access-token',
      refreshToken: 'placeholder-refresh-token',
      userId: 'employee-id',
      email: 'employee@example.com',
      companyId: 'company-id',
      membershipId: 'employee-membership-id',
      companyName: 'My Company',
      fullName: 'Hadir Employee',
      roles: <String>['EMPLOYEE'],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          authControllerProvider.overrideWith(
            (ref) =>
                AuthController.forTest(const AuthState.authenticated(session)),
          ),
          deviceBindingProvider.overrideWith(
            (ref) async => const DeviceBinding(
              status: 'approved',
              requiresApproval: false,
            ),
          ),
        ],
        child: const MaterialApp(
          locale: Locale('ar'),
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: <LocalizationsDelegate<dynamic>>[
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
          ],
          home: RoleWorkspaceScreen(),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('مساحة عمل الموظف'), findsOneWidget);
    expect(find.text('الرئيسية'), findsOneWidget);
    expect(find.text('الحضور'), findsOneWidget);
    expect(find.text('المهام'), findsOneWidget);
    expect(find.text('الطلبات'), findsOneWidget);
    expect(find.text('الملف الشخصي'), findsOneWidget);
    expect(find.text('الفريق'), findsNothing);
    await tester.tap(find.text('الملف الشخصي'));
    await tester.pumpAndSettle();
    expect(find.text('employee@example.com'), findsOneWidget);
    expect(find.text('دعوات الموظفين'), findsNothing);
  });
}
