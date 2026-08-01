import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:haydar/core/device/installation_identity.dart';

void main() {
  test('generates a standards-shaped UUID v4 installation identity', () {
    final value = generateInstallationUuid(Random(42));

    expect(
      value,
      matches(
        RegExp(
          r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        ),
      ),
    );
  });
}
