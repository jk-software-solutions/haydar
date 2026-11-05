import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/device/wifi_info.dart';
import '../../auth/application/auth_api.dart';
import '../application/organization_admin_api.dart';

class BranchShiftAdminScreen extends ConsumerStatefulWidget {
  const BranchShiftAdminScreen({
    required this.session,
    this.canManageBranches = true,
    super.key,
  });

  final AuthSession session;
  final bool canManageBranches;

  @override
  ConsumerState<BranchShiftAdminScreen> createState() =>
      _BranchShiftAdminScreenState();
}

class _BranchShiftAdminScreenState
    extends ConsumerState<BranchShiftAdminScreen> {
  List<AdminBranch>? _branches;
  List<AdminShift>? _shifts;
  final Set<String> _selectedBranches = <String>{};
  final Set<String> _selectedShifts = <String>{};
  String? _error;
  bool _deleting = false;
  String? _wifiBusyBranchId;

  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _branches = null;
      _shifts = null;
      _error = null;
      _selectedBranches.clear();
      _selectedShifts.clear();
    });
    try {
      final api = ref.read(organizationAdminApiProvider);
      final values = await Future.wait<Object>(<Future<Object>>[
        api.listBranches(widget.session),
        api.listShifts(widget.session),
      ]);
      if (mounted) {
        setState(() {
          _branches = values[0] as List<AdminBranch>;
          _shifts = values[1] as List<AdminShift>;
        });
      }
    } on DioException catch (error) {
      if (mounted) setState(() => _error = _problemDetail(error));
    }
  }

  Future<void> _deleteBranches(Iterable<AdminBranch> branches) async {
    await _deleteSelected(
      count: branches.length,
      run: () async {
        final api = ref.read(organizationAdminApiProvider);
        for (final branch in branches) {
          await api.deleteBranch(widget.session, branch);
        }
      },
    );
  }

  Future<void> _deleteShifts(Iterable<AdminShift> shifts) async {
    await _deleteSelected(
      count: shifts.length,
      run: () async {
        final api = ref.read(organizationAdminApiProvider);
        for (final shift in shifts) {
          await api.deleteShift(widget.session, shift);
        }
      },
    );
  }

  Future<void> _deleteSelected({
    required int count,
    required Future<void> Function() run,
  }) async {
    if (count == 0 || _deleting) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(_ar ? 'تأكيد الحذف' : 'Confirm delete'),
        content: Text(
          _ar
              ? 'سيتم أرشفة $count عنصر وإخفاؤه من القوائم النشطة.'
              : '$count item(s) will be archived and removed from active lists.',
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(_ar ? 'إلغاء' : 'Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(_ar ? 'حذف' : 'Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _deleting = true);
    try {
      await run();
      await _load();
    } on DioException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(_problemDetail(error))));
      }
    } finally {
      if (mounted) setState(() => _deleting = false);
    }
  }

  Future<void> _addWifiNetwork(AdminBranch branch) async {
    if (!widget.canManageBranches || _wifiBusyBranchId != null) return;
    List<WifiSnapshot> networks;
    try {
      networks = await WifiInfo.scanNetworks();
    } on Object catch (_) {
      networks = const <WifiSnapshot>[];
    }
    if (!mounted) return;
    if (networks.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _ar
                ? 'لم تظهر شبكات. فعّل Wi‑Fi والموقع واسمح للتطبيق بالوصول ثم أعد الفحص.'
                : 'No networks found. Turn on Wi‑Fi and Location, allow access, then scan again.',
          ),
        ),
      );
      return;
    }
    final selected = await showDialog<WifiSnapshot>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(_ar ? 'اختر شبكة Wi‑Fi' : 'Choose a Wi‑Fi network'),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.separated(
            shrinkWrap: true,
            itemCount: networks.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final network = networks[index];
              return ListTile(
                leading: const Icon(Icons.wifi_rounded),
                title: Text(network.ssid),
                subtitle: Text(network.bssid),
                trailing: network.level == null
                    ? null
                    : Text('${network.level} dBm'),
                onTap: () => Navigator.of(context).pop(network),
              );
            },
          ),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(_ar ? 'إلغاء' : 'Cancel'),
          ),
        ],
      ),
    );
    if (selected == null || !mounted) return;
    if (branch.wifiNetworks.any(
      (item) => item.bssid.toLowerCase() == selected.bssid.toLowerCase(),
    )) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _ar ? 'هذه الشبكة مضافة مسبقاً.' : 'This network is already added.',
          ),
        ),
      );
      return;
    }
    await _saveWifi(branch, <AdminWifiNetwork>[
      ...branch.wifiNetworks,
      AdminWifiNetwork(ssid: selected.ssid, bssid: selected.bssid),
    ]);
  }

  Future<void> _removeWifiNetwork(
    AdminBranch branch,
    AdminWifiNetwork network,
  ) async {
    if (!widget.canManageBranches || _wifiBusyBranchId != null) return;
    await _saveWifi(
      branch,
      branch.wifiNetworks
          .where((item) => item != network)
          .toList(growable: false),
    );
  }

  Future<void> _saveWifi(
    AdminBranch branch,
    List<AdminWifiNetwork> networks,
  ) async {
    setState(() => _wifiBusyBranchId = branch.id);
    try {
      final updated = await ref
          .read(organizationAdminApiProvider)
          .updateBranchWifi(widget.session, branch, networks);
      if (!mounted) return;
      final index = _branches?.indexWhere((item) => item.id == branch.id) ?? -1;
      if (index >= 0) {
        setState(() => _branches![index] = updated);
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_ar ? 'تم حفظ شبكة الفرع.' : 'Branch Wi‑Fi saved.'),
        ),
      );
    } on DioException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(_problemDetail(error))));
      }
    } finally {
      if (mounted) setState(() => _wifiBusyBranchId = null);
    }
  }

  @override
  Widget build(BuildContext context) => DefaultTabController(
    length: 3,
    child: Scaffold(
      appBar: AppBar(
        title: Text(_ar ? 'الفروع والورديات' : 'Branches and shifts'),
        bottom: TabBar(
          tabs: <Widget>[
            Tab(text: _ar ? 'الفروع' : 'Branches'),
            Tab(text: _ar ? 'الورديات' : 'Shifts'),
            Tab(text: _ar ? 'Wi‑Fi' : 'Wi‑Fi'),
          ],
        ),
      ),
      body: _branches == null || _shifts == null
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator()
                  : Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          Text(_error!, textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          FilledButton(
                            onPressed: _load,
                            child: Text(_ar ? 'إعادة المحاولة' : 'Retry'),
                          ),
                        ],
                      ),
                    ),
            )
          : TabBarView(
              children: <Widget>[
                _BranchList(
                  branches: _branches!,
                  selected: _selectedBranches,
                  deleting: _deleting,
                  ar: _ar,
                  onChanged: (id, selected) => setState(
                    () => selected
                        ? _selectedBranches.add(id)
                        : _selectedBranches.remove(id),
                  ),
                  onDeleteOne: (branch) =>
                      _deleteBranches(<AdminBranch>[branch]),
                  onDeleteSelected: () => _deleteBranches(
                    _branches!.where(
                      (branch) => _selectedBranches.contains(branch.id),
                    ),
                  ),
                ),
                _ShiftList(
                  shifts: _shifts!,
                  selected: _selectedShifts,
                  deleting: _deleting,
                  ar: _ar,
                  onChanged: (id, selected) => setState(
                    () => selected
                        ? _selectedShifts.add(id)
                        : _selectedShifts.remove(id),
                  ),
                  onDeleteOne: (shift) => _deleteShifts(<AdminShift>[shift]),
                  onDeleteSelected: () => _deleteShifts(
                    _shifts!.where(
                      (shift) => _selectedShifts.contains(shift.id),
                    ),
                  ),
                ),
                _WifiList(
                  branches: _branches!,
                  canManage: widget.canManageBranches,
                  busyBranchId: _wifiBusyBranchId,
                  ar: _ar,
                  onAdd: _addWifiNetwork,
                  onRemove: _removeWifiNetwork,
                ),
              ],
            ),
    ),
  );
}

class _BranchList extends StatelessWidget {
  const _BranchList({
    required this.branches,
    required this.selected,
    required this.deleting,
    required this.ar,
    required this.onChanged,
    required this.onDeleteOne,
    required this.onDeleteSelected,
  });

  final List<AdminBranch> branches;
  final Set<String> selected;
  final bool deleting;
  final bool ar;
  final void Function(String id, bool selected) onChanged;
  final void Function(AdminBranch branch) onDeleteOne;
  final VoidCallback onDeleteSelected;

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
    children: <Widget>[
      _BulkDeleteBar(
        count: selected.length,
        deleting: deleting,
        ar: ar,
        onPressed: onDeleteSelected,
      ),
      if (branches.isEmpty)
        _EmptyCard(text: ar ? 'لا توجد فروع نشطة.' : 'No active branches.'),
      for (final branch in branches)
        Card(
          child: CheckboxListTile(
            value: selected.contains(branch.id),
            onChanged: deleting
                ? null
                : (value) => onChanged(branch.id, value ?? false),
            title: Text(branch.name),
            subtitle: Text(
              '${branch.code} · ${branch.latitude}, ${branch.longitude} · '
              '${branch.geofenceRadiusM}m',
            ),
            secondary: IconButton(
              tooltip: ar ? 'حذف' : 'Delete',
              onPressed: deleting ? null : () => onDeleteOne(branch),
              icon: const Icon(Icons.delete_outline),
            ),
          ),
        ),
    ],
  );
}

class _ShiftList extends StatelessWidget {
  const _ShiftList({
    required this.shifts,
    required this.selected,
    required this.deleting,
    required this.ar,
    required this.onChanged,
    required this.onDeleteOne,
    required this.onDeleteSelected,
  });

  final List<AdminShift> shifts;
  final Set<String> selected;
  final bool deleting;
  final bool ar;
  final void Function(String id, bool selected) onChanged;
  final void Function(AdminShift shift) onDeleteOne;
  final VoidCallback onDeleteSelected;

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
    children: <Widget>[
      _BulkDeleteBar(
        count: selected.length,
        deleting: deleting,
        ar: ar,
        onPressed: onDeleteSelected,
      ),
      if (shifts.isEmpty)
        _EmptyCard(text: ar ? 'لا توجد ورديات نشطة.' : 'No active shifts.'),
      for (final shift in shifts)
        Card(
          child: CheckboxListTile(
            value: selected.contains(shift.id),
            onChanged: deleting
                ? null
                : (value) => onChanged(shift.id, value ?? false),
            title: Text(shift.name),
            subtitle: Text(_shiftSubtitle(shift, ar)),
            secondary: IconButton(
              tooltip: ar ? 'حذف' : 'Delete',
              onPressed: deleting ? null : () => onDeleteOne(shift),
              icon: const Icon(Icons.delete_outline),
            ),
          ),
        ),
    ],
  );
}

class _WifiList extends StatelessWidget {
  const _WifiList({
    required this.branches,
    required this.canManage,
    required this.busyBranchId,
    required this.ar,
    required this.onAdd,
    required this.onRemove,
  });

  final List<AdminBranch> branches;
  final bool canManage;
  final String? busyBranchId;
  final bool ar;
  final Future<void> Function(AdminBranch branch) onAdd;
  final Future<void> Function(AdminBranch branch, AdminWifiNetwork network)
  onRemove;

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
    children: <Widget>[
      Card(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        child: ListTile(
          leading: const Icon(Icons.wifi_find_rounded),
          title: Text(
            ar ? 'شبكات الحضور عبر Wi‑Fi' : 'Wi‑Fi attendance networks',
          ),
          subtitle: Text(
            ar
                ? 'اضغط فحص الشبكات، اختر الشبكة، وسيُحفظ اسمها وعنوانها تلقائياً في الفرع.'
                : 'Scan, choose a network, and its name and address are saved automatically for the branch.',
          ),
        ),
      ),
      if (!canManage)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text(
            ar
                ? 'للتعديل تحتاج صلاحية إدارة الفروع.'
                : 'Branch management permission is required to edit Wi‑Fi.',
          ),
        ),
      if (branches.isEmpty)
        _EmptyCard(text: ar ? 'لا توجد فروع نشطة.' : 'No active branches.'),
      for (final branch in branches)
        Card(
          child: ExpansionTile(
            leading: const Icon(Icons.store_mall_directory_outlined),
            title: Text(branch.name),
            subtitle: Text(
              branch.wifiNetworks.isEmpty
                  ? (ar ? 'لا توجد شبكة مسجلة' : 'No network configured')
                  : '${branch.wifiNetworks.length} ${ar ? 'شبكة مسجلة' : 'network(s) configured'}',
            ),
            childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            children: <Widget>[
              for (final network in branch.wifiNetworks)
                ListTile(
                  dense: true,
                  leading: const Icon(Icons.wifi_rounded),
                  title: Text(network.ssid),
                  subtitle: Text(network.bssid),
                  trailing: canManage
                      ? IconButton(
                          tooltip: ar ? 'إزالة الشبكة' : 'Remove network',
                          onPressed: busyBranchId == branch.id
                              ? null
                              : () => onRemove(branch, network),
                          icon: const Icon(Icons.delete_outline),
                        )
                      : null,
                ),
              Align(
                alignment: AlignmentDirectional.centerStart,
                child: FilledButton.icon(
                  onPressed: !canManage || busyBranchId != null
                      ? null
                      : () => onAdd(branch),
                  icon: busyBranchId == branch.id
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.wifi_find_rounded),
                  label: Text(ar ? 'فحص وإضافة شبكة' : 'Scan and add network'),
                ),
              ),
            ],
          ),
        ),
    ],
  );
}

class _BulkDeleteBar extends StatelessWidget {
  const _BulkDeleteBar({
    required this.count,
    required this.deleting,
    required this.ar,
    required this.onPressed,
  });

  final int count;
  final bool deleting;
  final bool ar;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: FilledButton.icon(
      onPressed: count == 0 || deleting ? null : onPressed,
      icon: deleting
          ? const SizedBox.square(
              dimension: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.delete_sweep_outlined),
      label: Text(ar ? 'حذف المحدد ($count)' : 'Delete selected ($count)'),
    ),
  );
}

class _EmptyCard extends StatelessWidget {
  const _EmptyCard({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(padding: const EdgeInsets.all(20), child: Text(text)),
  );
}

String _shiftSubtitle(AdminShift shift, bool ar) {
  final periods = shift.periods.isEmpty
      ? '${_shortTime(shift.startTime)}-${_shortTime(shift.endTime)}'
      : shift.periods
            .map(
              (period) =>
                  '${_shortTime(period.startTime)}-${_shortTime(period.endTime)}',
            )
            .join(' · ');
  final location = shift.locationPolicy == 'location_not_required'
      ? (ar ? 'بدون شرط موقع' : 'No location required')
      : (ar ? 'يتطلب موقع الفرع' : 'Branch location required');
  return '${shift.code} · $periods · ${shift.workingDays.length} '
      '${ar ? 'أيام' : 'days'} · $location';
}

String _shortTime(String value) =>
    value.length >= 5 ? value.substring(0, 5) : value;

String _problemDetail(DioException error) {
  final data = error.response?.data;
  if (data is Map<String, dynamic>) {
    return data['detail'] as String? ??
        data['title'] as String? ??
        data['code'] as String? ??
        error.message ??
        'Request failed';
  }
  return error.message ?? 'Request failed';
}
