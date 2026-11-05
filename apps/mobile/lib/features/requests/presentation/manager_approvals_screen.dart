import 'dart:async';

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
  Timer? _refreshTimer;
  bool _loading = true;
  String? _error;
  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  String _twoDigits(int value) => value.toString().padLeft(2, '0');

  String _formatDateTime(String raw) {
    final parsed = DateTime.tryParse(raw);
    if (parsed == null) return raw;
    final value = parsed.toLocal();
    if (!_ar) {
      return '${_twoDigits(value.day)}/${_twoDigits(value.month)}/${value.year} '
          '${_twoDigits(value.hour)}:${_twoDigits(value.minute)}';
    }
    const months = <String>[
      'يناير',
      'فبراير',
      'مارس',
      'أبريل',
      'مايو',
      'يونيو',
      'يوليو',
      'أغسطس',
      'سبتمبر',
      'أكتوبر',
      'نوفمبر',
      'ديسمبر',
    ];
    final hour = value.hour % 12 == 0 ? 12 : value.hour % 12;
    final period = value.hour < 12 ? 'ص' : 'م';
    return '${value.day} ${months[value.month - 1]} ${value.year}، '
        '${_twoDigits(hour)}:${_twoDigits(value.minute)} $period';
  }

  String _formatRequestWindow(RequestItem item) {
    if (item.kind == 'leave') {
      return '${_formatDateTime(item.from)} – ${_formatDateTime(item.to)}';
    }
    final exitLabel = _ar ? 'الخروج' : 'Exit';
    final returnLabel = _ar ? 'العودة' : 'Return';
    return '$exitLabel: ${_formatDateTime(item.from)}\n'
        '$returnLabel: ${_formatDateTime(item.to)}';
  }

  String _typeLabel(RequestItem item) {
    if (item.kind == 'leave') return _ar ? 'إجازة' : 'Leave';
    return switch (item.type) {
      'one_hour' => _ar ? 'ساعة واحدة' : 'One hour',
      'multiple_hours' => _ar ? 'فترة محددة' : 'Specific period',
      'until_shift_end' => _ar ? 'حتى نهاية الوردية' : 'Until shift end',
      _ => _ar ? 'استئذان مخصص' : 'Custom permission',
    };
  }

  String _statusLabel(String status) => switch (status) {
    'pending' => _ar ? 'قيد الانتظار' : 'Pending',
    'approved' => _ar ? 'معتمد' : 'Approved',
    'rejected' => _ar ? 'مرفوض' : 'Rejected',
    _ => status,
  };

  @override
  void initState() {
    super.initState();
    _refresh();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 15),
      (_) => unawaited(_refresh()),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
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
                            const SizedBox(height: 10),
                            if (item.employeeName.isNotEmpty)
                              Text(
                                item.employeeName,
                                style: Theme.of(context).textTheme.titleSmall,
                              ),
                            if (item.employeeEmail.isNotEmpty)
                              Text(
                                item.employeeEmail,
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            const SizedBox(height: 8),
                            Text(_typeLabel(item)),
                            const SizedBox(height: 4),
                            Text(_formatRequestWindow(item)),
                            const SizedBox(height: 4),
                            Text('${_ar ? 'السبب' : 'Reason'}: ${item.reason}'),
                            const SizedBox(height: 4),
                            Text(
                              '${_ar ? 'الحالة' : 'Status'}: ${_statusLabel(item.status)}',
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
