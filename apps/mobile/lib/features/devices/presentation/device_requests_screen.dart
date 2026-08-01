import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../auth/application/auth_controller.dart';
import '../application/device_api.dart';

bool _canManageDevices(List<String> roles) {
  return roles.any(
    (role) =>
        role == 'OWNER' ||
        role == 'MANAGER' ||
        role == 'COMPANY_MANAGER' ||
        role == 'HR' ||
        role == 'HR_OFFICER',
  );
}

class DeviceRequestsScreen extends ConsumerStatefulWidget {
  const DeviceRequestsScreen({super.key});

  @override
  ConsumerState<DeviceRequestsScreen> createState() =>
      _DeviceRequestsScreenState();
}

class _DeviceRequestsScreenState extends ConsumerState<DeviceRequestsScreen> {
  List<DeviceChange> _items = const <DeviceChange>[];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    final roles = ref.read(authControllerProvider).session?.roles ?? <String>[];
    if (_canManageDevices(roles)) {
      Future<void>.microtask(_load);
    } else {
      _loading = false;
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await ref.read(deviceApiProvider).listPendingChanges();
      if (mounted) {
        setState(() => _items = items);
      }
    } on Object {
      if (mounted) {
        setState(
          () => _error = AppLocalizations.of(context).deviceRequestsError,
        );
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _review(DeviceChange change, bool approve) async {
    try {
      await ref
          .read(deviceApiProvider)
          .reviewChange(change.id, approve: approve);
      await _load();
    } on Object {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(AppLocalizations.of(context).deviceReviewError),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final roles =
        ref.watch(authControllerProvider).session?.roles ?? <String>[];
    if (!_canManageDevices(roles)) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.deviceRequestsTitle)),
        body: Center(child: Text(l10n.permissionDenied)),
      );
    }
    return Scaffold(
      appBar: AppBar(title: Text(l10n.deviceRequestsTitle)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? Center(
              child: OutlinedButton(
                onPressed: _load,
                child: Text(l10n.retryButton),
              ),
            )
          : _items.isEmpty
          ? Center(child: Text(l10n.noDeviceRequests))
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: _items.length,
                separatorBuilder: (_, _) => const SizedBox(height: 8),
                itemBuilder: (context, index) {
                  final item = _items[index];
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: <Widget>[
                          Text(item.reason),
                          const SizedBox(height: 12),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: <Widget>[
                              TextButton(
                                onPressed: () => _review(item, false),
                                child: Text(l10n.rejectButton),
                              ),
                              const SizedBox(width: 8),
                              FilledButton(
                                onPressed: () => _review(item, true),
                                child: Text(l10n.approveButton),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
    );
  }
}
