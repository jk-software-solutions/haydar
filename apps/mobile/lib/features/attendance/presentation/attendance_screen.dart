import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:local_auth/local_auth.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../auth/application/auth_api.dart';
import '../application/attendance_api.dart';

class AttendanceScreen extends ConsumerStatefulWidget {
  const AttendanceScreen({
    required this.session,
    this.managerMode = false,
    super.key,
  });

  final AuthSession session;
  final bool managerMode;

  @override
  ConsumerState<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends ConsumerState<AttendanceScreen> {
  final LocalAuthentication _localAuthentication = LocalAuthentication();
  List<AttendanceRecord> _records = <AttendanceRecord>[];
  List<PresenceChallenge> _presence = <PresenceChallenge>[];
  bool _loading = true;
  bool _submitting = false;
  String? _error;
  int? _lastDistance;

  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';
  AttendanceRecord? get _openRecord =>
      _records.where((record) => record.isOpen).firstOrNull;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    try {
      final api = ref.read(attendanceApiProvider);
      final records = await api.list(
        widget.session,
        allCompany: widget.managerMode,
      );
      final presence = widget.managerMode
          ? <PresenceChallenge>[]
          : await api.presenceChallenges(widget.session);
      if (mounted) {
        setState(() {
          _records = records;
          _presence = presence;
          _error = null;
        });
      }
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<Position> _position() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      throw StateError(
        _ar
            ? 'خدمة الموقع متوقفة. فعّل GPS ثم أعد المحاولة.'
            : 'Location services are disabled. Enable GPS and retry.',
      );
    }
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      throw StateError(
        _ar
            ? 'صلاحية الموقع مطلوبة لتسجيل الحضور.'
            : 'Location permission is required for attendance.',
      );
    }
    return Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 20),
      ),
    );
  }

  Future<bool> _authenticateLocally() async {
    try {
      if (!await _localAuthentication.isDeviceSupported()) return false;
      return _localAuthentication.authenticate(
        localizedReason: _ar
            ? 'أكد عملية الحضور ببصمة الجهاز'
            : 'Confirm attendance using device biometrics',
        biometricOnly: true,
        persistAcrossBackgrounding: true,
      );
    } on Object {
      return false;
    }
  }

  Future<void> _submit({required String method, String? qrToken}) async {
    if (_submitting) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final position = await _position();
      final biometric = await _authenticateLocally();
      final api = ref.read(attendanceApiProvider);
      if (_openRecord == null) {
        await api.checkIn(
          session: widget.session,
          latitude: position.latitude,
          longitude: position.longitude,
          method: method,
          biometricConfirmed: biometric,
          qrToken: qrToken,
        );
      } else {
        await api.checkOut(
          session: widget.session,
          latitude: position.latitude,
          longitude: position.longitude,
          method: method,
          biometricConfirmed: biometric,
          qrToken: qrToken,
        );
      }
      await _refresh();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              _ar
                  ? 'تم تسجيل العملية بنجاح.'
                  : 'Attendance recorded successfully.',
            ),
          ),
        );
      }
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  String _message(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map<String, dynamic> && data['detail'] is String) {
        return data['detail'] as String;
      }
      if (error.type == DioExceptionType.connectionError ||
          error.type == DioExceptionType.connectionTimeout) {
        return _ar
            ? 'لا يوجد اتصال بالخادم. تحقق من الإنترنت.'
            : 'The server is unreachable. Check your connection.';
      }
    }
    return error.toString().replaceFirst('Bad state: ', '');
  }

  Future<void> _scanQr() async {
    final token = await Navigator.of(context).push<String>(
      MaterialPageRoute<String>(builder: (_) => const _QrScannerPage()),
    );
    if (token != null && mounted) await _submit(method: 'qr', qrToken: token);
  }

  Future<void> _respondToPresence(PresenceChallenge challenge) async {
    setState(() => _submitting = true);
    try {
      final position = await _position();
      await ref
          .read(attendanceApiProvider)
          .respondToPresence(
            session: widget.session,
            requestId: challenge.requestId,
            latitude: position.latitude,
            longitude: position.longitude,
          );
      await _refresh();
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    final open = _openRecord;
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: <Widget>[
          Text(
            _ar ? 'الحضور والانصراف' : 'Attendance',
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          Text(
            open == null
                ? (_ar
                      ? 'لا توجد جلسة حضور مفتوحة.'
                      : 'No attendance session is open.')
                : (_ar
                      ? 'أنت مسجل حضور حاليًا.'
                      : 'You are currently checked in.'),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Material(
                color: Theme.of(context).colorScheme.errorContainer,
                borderRadius: BorderRadius.circular(12),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Text(_error!),
                ),
              ),
            ),
          if (_presence.any((item) => item.canRespond)) ...<Widget>[
            const SizedBox(height: 14),
            ..._presence
                .where((item) => item.canRespond)
                .map(
                  (challenge) => Card(
                    color: Theme.of(context).colorScheme.tertiaryContainer,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: <Widget>[
                          Text(
                            _ar
                                ? 'طلب إثبات تواجد عاجل'
                                : 'Urgent presence check',
                            style: Theme.of(context).textTheme.titleMedium
                                ?.copyWith(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 6),
                          Text(challenge.message),
                          const SizedBox(height: 8),
                          Text(
                            '${_ar ? 'المهلة' : 'Deadline'}: ${challenge.deadlineAt?.toLocal()}',
                          ),
                          const SizedBox(height: 10),
                          FilledButton(
                            onPressed: _submitting
                                ? null
                                : () => _respondToPresence(challenge),
                            child: Text(
                              _ar
                                  ? 'تأكيد التواجد الآن'
                                  : 'Confirm presence now',
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
          ],
          const SizedBox(height: 20),
          if (!widget.managerMode) ...<Widget>[
            FilledButton.icon(
              onPressed: _submitting ? null : () => _submit(method: 'gps'),
              icon: Icon(
                open == null ? Icons.login_rounded : Icons.logout_rounded,
              ),
              label: Text(
                open == null
                    ? (_ar ? 'تسجيل حضور عبر GPS' : 'Check in with GPS')
                    : (_ar ? 'تسجيل انصراف عبر GPS' : 'Check out with GPS'),
              ),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: _submitting ? null : _scanQr,
              icon: const Icon(Icons.qr_code_scanner_rounded),
              label: Text(_ar ? 'مسح رمز QR' : 'Scan branch QR'),
            ),
          ],
          if (_lastDistance != null)
            Text(
              '${_ar ? 'المسافة عن الفرع' : 'Distance from branch'}: $_lastDistance m',
            ),
          const SizedBox(height: 28),
          Text(
            _ar ? 'السجل الأخير' : 'Recent history',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 10),
          if (_records.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Text(_ar ? 'لا توجد سجلات بعد.' : 'No records yet.'),
              ),
            ),
          ..._records
              .take(31)
              .map(
                (record) => Card(
                  child: ListTile(
                    leading: Icon(
                      record.status == 'on_time'
                          ? Icons.check_circle_outline
                          : Icons.schedule_rounded,
                    ),
                    title: Text('${record.workDate} · ${record.status}'),
                    subtitle: Text(
                      '${_ar ? 'ساعات العمل' : 'Worked'}: '
                      '${record.workedMinutes ~/ 60}h '
                      '${record.workedMinutes % 60}m · '
                      '${_ar ? 'التأخير' : 'Late'}: '
                      '${record.lateMinutes}m',
                    ),
                  ),
                ),
              ),
        ],
      ),
    );
  }
}

class _QrScannerPage extends StatefulWidget {
  const _QrScannerPage();

  @override
  State<_QrScannerPage> createState() => _QrScannerPageState();
}

class _QrScannerPageState extends State<_QrScannerPage> {
  bool _completed = false;

  @override
  Widget build(BuildContext context) {
    final ar = Localizations.localeOf(context).languageCode == 'ar';
    return Scaffold(
      appBar: AppBar(title: Text(ar ? 'مسح رمز الفرع' : 'Scan branch QR')),
      body: MobileScanner(
        onDetect: (capture) {
          if (_completed) return;
          final value = capture.barcodes.firstOrNull?.rawValue;
          if (value != null && value.isNotEmpty) {
            _completed = true;
            Navigator.of(context).pop(value);
          }
        },
      ),
    );
  }
}
