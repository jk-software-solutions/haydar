import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../auth/application/auth_api.dart';
import '../../team/application/team_api.dart';

final organizationAdminApiProvider = Provider<OrganizationAdminApi>(
  (ref) => OrganizationAdminApi(ref.watch(dioProvider)),
);

class OrganizationAdminApi {
  OrganizationAdminApi(this.dio);

  final Dio dio;

  Options _options(AuthSession session) => Options(
    headers: <String, String>{'Authorization': 'Bearer ${session.accessToken}'},
  );

  Future<OwnerAccessData> loadOwnerAccess(AuthSession session) async {
    final responses = await Future.wait<Response<dynamic>>(<
      Future<Response<dynamic>>
    >[
      dio.get<dynamic>('/employees?page_size=100', options: _options(session)),
      dio.get<dynamic>('/members/access-catalog', options: _options(session)),
      dio.get<dynamic>('/members/access', options: _options(session)),
      dio.get<dynamic>('/branches?page_size=100', options: _options(session)),
      dio.get<dynamic>('/departments', options: _options(session)),
      dio.get<dynamic>(
        '/groups?page_size=100&include_inactive=true',
        options: _options(session),
      ),
    ]);
    return OwnerAccessData(
      members: _items(
        responses[0].data,
      ).map(TeamMember.fromJson).toList(growable: false),
      permissions: _maps(
        responses[1].data,
      ).map(PermissionOption.fromJson).toList(growable: false),
      access: _maps(
        responses[2].data,
      ).map(MemberAccess.fromJson).toList(growable: false),
      branches: _items(
        responses[3].data,
      ).map(NamedOption.fromJson).toList(growable: false),
      departments: _items(
        responses[4].data,
      ).map(NamedOption.fromJson).toList(growable: false),
      groups: _items(
        responses[5].data,
      ).map(NamedOption.fromJson).toList(growable: false),
    );
  }

  Future<MemberAccess> updateMemberAccess(
    AuthSession session,
    MemberAccess access,
  ) async {
    final response = await dio.put<Map<String, dynamic>>(
      '/members/${access.membershipId}/access',
      options: _options(session),
      data: access.toJson(),
    );
    return MemberAccess.fromJson(response.data ?? <String, dynamic>{});
  }

  Future<List<OrganizationGroup>> listGroups(AuthSession session) async {
    final response = await dio.get<dynamic>(
      '/groups?page_size=100&include_inactive=true',
      options: _options(session),
    );
    return _items(
      response.data,
    ).map(OrganizationGroup.fromJson).toList(growable: false);
  }

  Future<OrganizationGroup> createGroup(
    AuthSession session, {
    required String code,
    required String name,
    required String description,
  }) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/groups',
      options: _options(session),
      data: <String, dynamic>{
        'code': code.trim().toUpperCase(),
        'name': name.trim(),
        'description': description.trim(),
      },
    );
    return OrganizationGroup.fromJson(response.data ?? <String, dynamic>{});
  }

  Future<OrganizationGroup> updateGroup(
    AuthSession session,
    OrganizationGroup group,
  ) async {
    final response = await dio.patch<Map<String, dynamic>>(
      '/groups/${group.id}',
      options: _options(session),
      data: <String, dynamic>{
        'name': group.name,
        'description': group.description,
        'is_active': group.isActive,
        'version': group.version,
      },
    );
    return OrganizationGroup.fromJson(response.data ?? <String, dynamic>{});
  }

  Future<OrganizationGroup> replaceGroupMembers(
    AuthSession session,
    String groupId,
    Set<String> membershipIds,
  ) async {
    final response = await dio.put<Map<String, dynamic>>(
      '/groups/$groupId/members',
      options: _options(session),
      data: <String, dynamic>{
        'membership_ids': membershipIds.toList(growable: false),
      },
    );
    return OrganizationGroup.fromJson(response.data ?? <String, dynamic>{});
  }

  Future<List<AdminBranch>> listBranches(AuthSession session) async {
    final response = await dio.get<dynamic>(
      '/branches?page_size=100',
      options: _options(session),
    );
    return _items(
      response.data,
    ).map(AdminBranch.fromJson).toList(growable: false);
  }

  Future<void> deleteBranch(AuthSession session, AdminBranch branch) async {
    await dio.delete<dynamic>(
      '/branches/${branch.id}?version=${branch.version}',
      options: _options(session),
    );
  }

  Future<AdminBranch> updateBranchWifi(
    AuthSession session,
    AdminBranch branch,
    List<AdminWifiNetwork> networks,
  ) async {
    final response = await dio.patch<Map<String, dynamic>>(
      '/branches/${branch.id}',
      options: _options(session),
      data: <String, dynamic>{
        'version': branch.version,
        'wifi_networks': networks.map((item) => item.toJson()).toList(),
      },
    );
    return AdminBranch.fromJson(response.data ?? <String, dynamic>{});
  }

  Future<List<AdminShift>> listShifts(AuthSession session) async {
    final response = await dio.get<dynamic>(
      '/shifts?page_size=100',
      options: _options(session),
    );
    return _items(
      response.data,
    ).map(AdminShift.fromJson).toList(growable: false);
  }

  Future<void> deleteShift(AuthSession session, AdminShift shift) async {
    await dio.delete<dynamic>(
      '/shifts/${shift.id}?version=${shift.version}',
      options: _options(session),
    );
  }
}

List<Map<String, dynamic>> _items(dynamic data) {
  if (data is Map<String, dynamic>) return _maps(data['items']);
  return _maps(data);
}

List<Map<String, dynamic>> _maps(dynamic data) =>
    (data as List<dynamic>? ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .toList(growable: false);

class OwnerAccessData {
  const OwnerAccessData({
    required this.members,
    required this.permissions,
    required this.access,
    required this.branches,
    required this.departments,
    required this.groups,
  });

  final List<TeamMember> members;
  final List<PermissionOption> permissions;
  final List<MemberAccess> access;
  final List<NamedOption> branches;
  final List<NamedOption> departments;
  final List<NamedOption> groups;
}

class NamedOption {
  const NamedOption({required this.id, required this.name});
  factory NamedOption.fromJson(Map<String, dynamic> json) => NamedOption(
    id: json['id'] as String? ?? '',
    name: json['name'] as String? ?? '',
  );
  final String id;
  final String name;
}

class PermissionOption {
  const PermissionOption({required this.code, required this.description});
  factory PermissionOption.fromJson(Map<String, dynamic> json) =>
      PermissionOption(
        code: json['code'] as String? ?? '',
        description: json['description'] as String? ?? '',
      );
  final String code;
  final String description;
}

class MemberAccess {
  const MemberAccess({
    required this.membershipId,
    required this.roleCodes,
    required this.permissionOverrides,
    required this.effectivePermissions,
    required this.branchIds,
    required this.departmentIds,
    required this.groupIds,
  });

  factory MemberAccess.fromJson(Map<String, dynamic> json) => MemberAccess(
    membershipId: json['membership_id'] as String? ?? '',
    roleCodes: _strings(json['role_codes']),
    permissionOverrides:
        (json['permission_overrides'] as Map<String, dynamic>? ??
                <String, dynamic>{})
            .map((key, value) => MapEntry(key, value == true)),
    effectivePermissions: _strings(json['effective_permissions']),
    branchIds: _strings(json['branch_ids']),
    departmentIds: _strings(json['department_ids']),
    groupIds: _strings(json['group_ids']),
  );

  final String membershipId;
  final List<String> roleCodes;
  final Map<String, bool> permissionOverrides;
  final List<String> effectivePermissions;
  final List<String> branchIds;
  final List<String> departmentIds;
  final List<String> groupIds;

  Map<String, dynamic> toJson() => <String, dynamic>{
    'role_codes': roleCodes,
    'permission_overrides': permissionOverrides,
    'branch_ids': branchIds,
    'department_ids': departmentIds,
    'group_ids': groupIds,
  };
}

class OrganizationGroup extends NamedOption {
  const OrganizationGroup({
    required super.id,
    required super.name,
    required this.code,
    required this.description,
    required this.isActive,
    required this.version,
    required this.membershipIds,
  });

  factory OrganizationGroup.fromJson(Map<String, dynamic> json) =>
      OrganizationGroup(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        code: json['code'] as String? ?? '',
        description: json['description'] as String? ?? '',
        isActive: json['is_active'] as bool? ?? true,
        version: json['version'] as int? ?? 1,
        membershipIds: _strings(json['membership_ids']),
      );

  final String code;
  final String description;
  final bool isActive;
  final int version;
  final List<String> membershipIds;
}

class AdminBranch extends NamedOption {
  const AdminBranch({
    required super.id,
    required super.name,
    required this.code,
    required this.fullAddress,
    required this.latitude,
    required this.longitude,
    required this.geofenceRadiusM,
    required this.wifiNetworks,
    required this.version,
  });

  factory AdminBranch.fromJson(Map<String, dynamic> json) => AdminBranch(
    id: json['id'] as String? ?? '',
    name: json['name'] as String? ?? '',
    code: json['code'] as String? ?? '',
    fullAddress: json['full_address'] as String? ?? '',
    latitude: '${json['latitude'] ?? ''}',
    longitude: '${json['longitude'] ?? ''}',
    geofenceRadiusM: json['geofence_radius_m'] as int? ?? 0,
    wifiNetworks: _maps(
      json['wifi_networks'],
    ).map(AdminWifiNetwork.fromJson).toList(growable: false),
    version: json['version'] as int? ?? 1,
  );

  final String code;
  final String fullAddress;
  final String latitude;
  final String longitude;
  final int geofenceRadiusM;
  final List<AdminWifiNetwork> wifiNetworks;
  final int version;
}

class AdminWifiNetwork {
  const AdminWifiNetwork({required this.ssid, required this.bssid});

  factory AdminWifiNetwork.fromJson(Map<String, dynamic> json) =>
      AdminWifiNetwork(
        ssid: json['ssid'] as String? ?? '',
        bssid: json['bssid'] as String? ?? '',
      );

  final String ssid;
  final String bssid;

  Map<String, dynamic> toJson() => <String, dynamic>{
    'ssid': ssid.trim(),
    'bssid': bssid.trim().toLowerCase(),
  };
}

class AdminShift extends NamedOption {
  const AdminShift({
    required super.id,
    required super.name,
    required this.code,
    required this.startTime,
    required this.endTime,
    required this.workingDays,
    required this.locationPolicy,
    required this.periods,
    required this.version,
  });

  factory AdminShift.fromJson(Map<String, dynamic> json) {
    final recurrence =
        json['recurrence'] as Map<String, dynamic>? ?? <String, dynamic>{};
    return AdminShift(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      code: json['code'] as String? ?? '',
      startTime: json['start_time'] as String? ?? '',
      endTime: json['end_time'] as String? ?? '',
      workingDays: _ints(json['working_days']),
      locationPolicy:
          recurrence['location_policy'] as String? ?? 'branch_required',
      periods: _maps(recurrence['periods'])
          .map(
            (item) => ShiftPeriod(
              startTime: item['start_time'] as String? ?? '',
              endTime: item['end_time'] as String? ?? '',
            ),
          )
          .toList(growable: false),
      version: json['version'] as int? ?? 1,
    );
  }

  final String code;
  final String startTime;
  final String endTime;
  final List<int> workingDays;
  final String locationPolicy;
  final List<ShiftPeriod> periods;
  final int version;
}

class ShiftPeriod {
  const ShiftPeriod({required this.startTime, required this.endTime});

  final String startTime;
  final String endTime;
}

List<String> _strings(dynamic value) => (value as List<dynamic>? ?? <dynamic>[])
    .map((item) => '$item')
    .toList(growable: false);

List<int> _ints(dynamic value) => (value as List<dynamic>? ?? <dynamic>[])
    .map((item) => item is int ? item : int.tryParse('$item'))
    .whereType<int>()
    .toList(growable: false);
