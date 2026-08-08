import 'package:flutter_test/flutter_test.dart';
import 'package:haydar/features/organization/application/organization_admin_api.dart';

void main() {
  test(
    'member access parses and serializes role permission and scope data',
    () {
      final access = MemberAccess.fromJson(<String, dynamic>{
        'membership_id': 'member-1',
        'role_codes': <String>['MANAGER', 'SUPERVISOR'],
        'permission_overrides': <String, bool>{
          'reports:view': true,
          'branches:manage': false,
        },
        'effective_permissions': <String>['members:view', 'reports:view'],
        'branch_ids': <String>['branch-1'],
        'department_ids': <String>['department-1'],
        'group_ids': <String>['group-1'],
      });

      expect(access.membershipId, 'member-1');
      expect(access.roleCodes, <String>['MANAGER', 'SUPERVISOR']);
      expect(access.permissionOverrides['branches:manage'], isFalse);
      expect(access.toJson(), <String, dynamic>{
        'role_codes': <String>['MANAGER', 'SUPERVISOR'],
        'permission_overrides': <String, bool>{
          'reports:view': true,
          'branches:manage': false,
        },
        'branch_ids': <String>['branch-1'],
        'department_ids': <String>['department-1'],
        'group_ids': <String>['group-1'],
      });
    },
  );

  test('operational group retains lifecycle version and members', () {
    final group = OrganizationGroup.fromJson(<String, dynamic>{
      'id': 'group-1',
      'code': 'OPS',
      'name': 'Operations',
      'description': 'Field operations',
      'is_active': false,
      'version': 4,
      'membership_ids': <String>['member-1', 'member-2'],
    });

    expect(group.code, 'OPS');
    expect(group.isActive, isFalse);
    expect(group.version, 4);
    expect(group.membershipIds, <String>['member-1', 'member-2']);
  });

  test('missing optional API arrays parse as empty collections', () {
    final access = MemberAccess.fromJson(<String, dynamic>{
      'membership_id': 'member-2',
    });

    expect(access.roleCodes, isEmpty);
    expect(access.permissionOverrides, isEmpty);
    expect(access.branchIds, isEmpty);
    expect(access.departmentIds, isEmpty);
    expect(access.groupIds, isEmpty);
  });
}
