import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_api.dart';
import '../application/request_api.dart';

class ManagerApprovalsScreen extends ConsumerStatefulWidget {
  const ManagerApprovalsScreen({required this.session, super.key});
  final AuthSession session;

  @override
  ConsumerState<ManagerApprovalsScreen> createState() =>
      _ManagerApprovalsScreenState();
}

class _ManagerApprovalsScreenState
    extends ConsumerState<ManagerApprovalsScreen> {
  List<RequestItem> _items = <RequestItem>[];
  bool _loading = true;
  String? _error;
  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    try {
      final api = ref.read(requestApiProvider);
      final values = await Future.wait(<Future<List<RequestItem>>>[
        api.permissions(widget.session, allCompany: true),
        api.leaves(widget.session, allCompany: true),
      ]);
      if (mounted) {
        setState(() {
          _items = <RequestItem>[...values[0], ...values[1]];
          _error = null;
        });
      }
    } on DioException catch (error) {
      final data = error.response?.data;
      if (mounted) {
        setState(
          () => _error = data is Map<String, dynamic>
              ? data['detail'] as String? ?? '$error'
              : '$error',
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _review(RequestItem item, String decision) async {
    try {
      await ref.read(requestApiProvider).review(widget.session, item, decision);
      await _refresh();
    } on DioException catch (error) {
      final data = error.response?.data;
      if (mounted) {
        setState(
          () => _error = data is Map<String, dynamic>
              ? data['detail'] as String? ?? '$error'
              : '$error',
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_ar ? 'الموافقات' : 'Approvals')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: <Widget>[
                  if (_error != null)
                    Card(
                      color: Theme.of(context).colorScheme.errorContainer,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Text(_error!),
                      ),
                    ),
                  if (_items.isEmpty)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Text(_ar ? 'لا توجد طلبات.' : 'No requests.'),
                      ),
                    ),
                  ..._items.map(
                    (item) => Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: <Widget>[
                            Text(
                              item.kind == 'leave'
                                  ? (_ar ? 'طلب إجازة' : 'Leave request')
                                  : (_ar
                                        ? 'طلب استئذان'
                                        : 'Permission request'),
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: 6),
                            Text(
                              '${item.from} – ${item.to}\n${item.reason}\n${item.status}',
                            ),
                            if (item.status == 'pending') ...<Widget>[
                              const SizedBox(height: 12),
                              Row(
                                children: <Widget>[
                                  Expanded(
                                    child: OutlinedButton(
                                      onPressed: () =>
                                          _review(item, 'rejected'),
                                      child: Text(_ar ? 'رفض' : 'Reject'),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: FilledButton(
                                      onPressed: () =>
                                          _review(item, 'approved'),
                                      child: Text(_ar ? 'قبول' : 'Approve'),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
