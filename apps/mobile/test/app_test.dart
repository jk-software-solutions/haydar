import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haydar/app/haydar_app.dart';

void main() {
  testWidgets('starts Arabic-first with correct RTL direction', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: HaydarApp()));
    await tester.pump();

    expect(find.text('HADIR | حاضر'), findsOneWidget);
    expect(find.text('حضور أوضح، وإدارة أسهل'), findsOneWidget);
    expect(
      Directionality.of(tester.element(find.text('HADIR | حاضر'))),
      TextDirection.rtl,
    );
  });

  testWidgets('switches the same application shell to English LTR', (
    tester,
  ) async {
    await tester.pumpWidget(const ProviderScope(child: HaydarApp()));
    await tester.pump();

    await tester.tap(find.text('English'));
    await tester.pump();

    expect(find.text('Attendance, clearly managed'), findsOneWidget);
    expect(
      Directionality.of(tester.element(find.text('HADIR | حاضر'))),
      TextDirection.ltr,
    );
  });
}
