import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../../../core/device/biometric_gate.dart';
import '../../../core/device/wifi_info.dart';
import '../../auth/application/auth_api.dart';
import '../../requests/application/request_api.dart';
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

class _AttendanceScreenState extends ConsumerState<AttendanceScreen>
    with WidgetsBindingObserver {
  List<AttendanceRecord> _records = <AttendanceRecord>[];
  List<RequestItem> _permissions = <RequestItem>[];
  List<PresenceChallenge> _presence = <PresenceChallenge>[];
  List<GeofenceExitEvent> _geofenceExits = <GeofenceExitEvent>[];
  bool _loading = true;
  bool _submitting = false;
  String? _error;
  int? _lastDistance;
  StreamSubscription<Position>? _locationSubscription;
  String? _monitoredRecordId;
  Timer? _clockTimer;
  String _biometricPolicy = 'optional';
  BiometricResult? _lastBiometricResult;
  var _managerAttendanceTab = 0;

  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';
  AttendanceRecord? get _openRecord =>
      _records.where((record) => record.isOpen).firstOrNull;

  /// A permission checkout closes the current record with `on_permission`.
  /// The next attendance action re-opens that record as a return event. Keep
  /// this state visible so the employee knows exactly what to press.
  AttendanceRecord? get _permissionReturnRecord {
    if (_openRecord != null) return null;
    final now = DateTime.now().toUtc();
    return _records.where((record) {
      if (record.status != 'on_permission' || record.checkedOutAt == null) {
        return false;
      }
      final checkout = record.checkedOutAt!.toUtc();
      return _permissions.any((item) {
        if (item.status != 'approved') return false;
        final starts = DateTime.tryParse(item.from)?.toUtc();
        final ends = DateTime.tryParse(item.to)?.toUtc();
        return starts != null &&
            ends != null &&
            !starts.isAfter(now) &&
            !ends.isBefore(checkout);
      });
    }).firstOrNull;
  }

  bool get _activePermission {
    final now = DateTime.now().toUtc();
    return _permissions.any((item) {
      if (item.status != 'approved') return false;
      final starts = DateTime.tryParse(item.from)?.toUtc();
      final ends = DateTime.tryParse(item.to)?.toUtc();
      return starts != null &&
          ends != null &&
          !now.isBefore(starts) &&
          !now.isAfter(ends);
    });
  }

  bool get _checkoutAllowed {
    final record = _openRecord;
    if (record == null || _activePermission) return true;
    final scheduledEnd = record.scheduledEndAt;
    return scheduledEnd == null ||
        !DateTime.now().toUtc().isBefore(scheduledEnd.toUtc());
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _clockTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      unawaited(_refresh());
    });
    _refresh();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _clockTimer?.cancel();
    unawaited(_stopGeofenceMonitor());
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _openRecord != null) {
      unawaited(_reportResumeLocation(_openRecord!));
    }
  }

  Future<void> _refresh() async {
    try {
      final api = ref.read(attendanceApiProvider);
      final biometricPolicy = widget.managerMode
          ? 'disabled'
          : await api.biometricPolicy(widget.session);
      final records = await api.list(
        widget.session,
        allCompany: widget.managerMode,
      );
      final permissions = widget.managerMode
          ? <RequestItem>[]
          : await ref.read(requestApiProvider).permissions(widget.session);
      final presence = widget.managerMode
          ? <PresenceChallenge>[]
          : await api.presenceChallenges(widget.session);
      final geofenceExits =
          widget.managerMode && widget.session.can('geofence_exits:view')
          ? await api.listGeofenceExits(widget.session)
          : <GeofenceExitEvent>[];
      if (mounted) {
        setState(() {
          _records = records;
          _permissions = permissions;
          _presence = presence;
          _geofenceExits = geofenceExits;
          _biometricPolicy = biometricPolicy;
          _error = null;
        });
        await _syncGeofenceMonitor();
      }
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _locationPermissionCode(LocationPermission permission) {
    return switch (permission) {
      LocationPermission.always => 'always',
      LocationPermission.whileInUse => 'while_in_use',
      LocationPermission.deniedForever => 'denied_forever',
      LocationPermission.denied => 'denied',
      LocationPermission.unableToDetermine => 'denied',
    };
  }

  Future<void> _reportMonitoringUnavailable(
    AttendanceRecord record,
    String permission,
  ) async {
    try {
      await ref
          .read(attendanceApiProvider)
          .reportGeofenceSample(
            session: widget.session,
            recordId: record.id,
            observedAt: DateTime.now().toUtc(),
            source: 'resume_check',
            locationPermission: permission,
          );
    } on Object {
      // The next refresh/resume retries; attendance itself remains usable.
    }
  }

  Future<void> _reportPosition(
    AttendanceRecord record,
    Position position,
    String source,
  ) async {
    try {
      final permission = await Geolocator.checkPermission();
      await ref
          .read(attendanceApiProvider)
          .reportGeofenceSample(
            session: widget.session,
            recordId: record.id,
            observedAt: position.timestamp,
            source: source,
            locationPermission: _locationPermissionCode(permission),
            latitude: position.latitude,
            longitude: position.longitude,
            accuracyM: position.accuracy.round(),
          );
    } on Object {
      // Monitoring is best effort and will retry on the next location sample.
    }
  }

  Future<void> _reportResumeLocation(AttendanceRecord record) async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      await _reportMonitoringUnavailable(record, 'service_disabled');
      return;
    }
    final permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever ||
        permission == LocationPermission.unableToDetermine) {
      await _reportMonitoringUnavailable(
        record,
        _locationPermissionCode(permission),
      );
      return;
    }
    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 20),
        ),
      );
      await _reportPosition(record, position, 'resume_check');
    } on Object {
      // The foreground stream remains the primary monitoring path.
    }
  }

  Future<void> _syncGeofenceMonitor() async {
    final record = _openRecord;
    if (widget.managerMode || record == null) {
      await _stopGeofenceMonitor();
      return;
    }
    if (_locationSubscription != null && _monitoredRecordId == record.id) {
      return;
    }
    await _stopGeofenceMonitor();
    _monitoredRecordId = record.id;
    if (!await Geolocator.isLocationServiceEnabled()) {
      await _reportMonitoringUnavailable(record, 'service_disabled');
      return;
    }
    final permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever ||
        permission == LocationPermission.unableToDetermine) {
      await _reportMonitoringUnavailable(
        record,
        _locationPermissionCode(permission),
      );
      return;
    }
    _locationSubscription =
        Geolocator.getPositionStream(
          locationSettings: AndroidSettings(
            accuracy: LocationAccuracy.high,
            distanceFilter: 25,
            intervalDuration: const Duration(seconds: 30),
            foregroundNotificationConfig: const ForegroundNotificationConfig(
              notificationTitle: 'DawamTech attendance monitoring',
              notificationText:
                  'Location is checked while your attendance session is open.',
              notificationChannelName: 'Attendance location monitoring',
              enableWakeLock: true,
              setOngoing: true,
            ),
          ),
        ).listen(
          (position) => unawaited(
            _reportPosition(record, position, 'foreground_service'),
          ),
          onError: (_) => unawaited(_reportResumeLocation(record)),
        );
  }

  Future<void> _stopGeofenceMonitor() async {
    final subscription = _locationSubscription;
    _locationSubscription = null;
    _monitoredRecordId = null;
    await subscription?.cancel();
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
    final result = await ref
        .read(biometricGateProvider)
        .confirm(
          policy: _biometricPolicy,
          localizedReason: _ar
              ? 'أكد عملية الحضور ببصمة الجهاز'
              : 'Confirm attendance using device biometrics',
        );
    if (mounted) setState(() => _lastBiometricResult = result);
    if (_biometricPolicy == 'required' && result != BiometricResult.confirmed) {
      throw StateError(_biometricMessage(result));
    }
    return result == BiometricResult.confirmed;
  }

  String _biometricMessage(BiometricResult result) => switch (result) {
    BiometricResult.confirmed =>
      _ar ? 'تم تأكيد البصمة.' : 'Biometric confirmation succeeded.',
    BiometricResult.skipped =>
      _ar ? 'البصمة معطلة.' : 'Biometrics are disabled.',
    BiometricResult.unavailable =>
      _ar
          ? 'هذا الجهاز لا يدعم البصمة المتاحة.'
          : 'Biometrics are unavailable on this device.',
    BiometricResult.notEnrolled =>
      _ar
          ? 'سجّل بصمة في إعدادات الجهاز أولاً.'
          : 'Enroll biometrics in device settings first.',
    BiometricResult.cancelled =>
      _ar ? 'أُلغي تأكيد البصمة.' : 'Biometric confirmation was cancelled.',
    BiometricResult.lockedOut =>
      _ar
          ? 'البصمة مقفلة مؤقتاً. افتح الجهاز ثم أعد المحاولة.'
          : 'Biometrics are locked. Unlock the device and retry.',
    BiometricResult.failed =>
      _ar ? 'تعذر إكمال تأكيد البصمة.' : 'Biometric confirmation failed.',
  };

  Future<void> _submit({required String method, String? qrToken}) async {
    if (_submitting) return;
    if (_openRecord != null && !_checkoutAllowed) {
      setState(() {
        _error = _ar
            ? 'لا يمكن تسجيل الانصراف قبل نهاية فترة الوردية. إذا كان لديك استئذان معتمد، انتظر بداية فترة الاستئذان.'
            : 'Check-out is available after the scheduled period ends, unless an approved permission is active.';
      });
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      var latitude = 0.0;
      var longitude = 0.0;
      WifiSnapshot? wifi;
      if (method == 'wifi') {
        wifi = await WifiInfo.current();
        if (wifi == null) {
          throw StateError(
            _ar
                ? 'تعذر قراءة شبكة Wi‑Fi الحالية. اتصل بشبكة الفرع وفعّل صلاحية الأجهزة القريبة ثم أعد المحاولة.'
                : 'Could not read the current Wi‑Fi network. Connect to the branch network, allow nearby-device access, and retry.',
          );
        }
      } else {
        final position = await _position();
        latitude = position.latitude;
        longitude = position.longitude;
      }
      final biometric = await _authenticateLocally();
      final api = ref.read(attendanceApiProvider);
      if (_openRecord == null) {
        await api.checkIn(
          session: widget.session,
          latitude: latitude,
          longitude: longitude,
          method: method,
          biometricConfirmed: biometric,
          qrToken: qrToken,
          wifiSsid: wifi?.ssid,
          wifiBssid: wifi?.bssid,
        );
      } else {
        await api.checkOut(
          session: widget.session,
          latitude: latitude,
          longitude: longitude,
          method: method,
          biometricConfirmed: biometric,
          qrToken: qrToken,
          wifiSsid: wifi?.ssid,
          wifiBssid: wifi?.bssid,
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

  Future<void> _showLocationMap(AttendanceRecord record) async {
    try {
      final events = await ref
          .read(attendanceApiProvider)
          .locationEvents(widget.session, record.id);
      final gpsEvents = events.where((event) => event.isGpsPoint).toList();
      if (!mounted) return;
      if (gpsEvents.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              _ar
                  ? 'لا توجد نقطة GPS محفوظة لهذا السجل. قد يكون الحضور عبر Wi‑Fi أو QR.'
                  : 'No GPS point is saved for this record. It may have been recorded by Wi‑Fi or QR.',
            ),
          ),
        );
        return;
      }
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) => _AttendanceLocationMapSheet(
          events: gpsEvents,
          arabic: _ar,
          recordDate: record.workDate,
        ),
      );
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    }
  }

  String _message(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map<String, dynamic>) {
        final code = data['code'] as String?;
        if (_ar) {
          final localized = switch (code) {
            'branch_not_assigned' =>
              'لم يتم تعيينك على فرع نشط. من الموقع افتح الموظف ثم «تعيين الفرع والوردية»، واختر فرعاً سارياً من تاريخ اليوم.',
            'branch_inactive' =>
              'الفرع المعيّن غير نشط. فعّل الفرع من صفحة الفروع ثم احفظ.',
            'shift_not_assigned' =>
              'لم يتم تعيين وردية نشطة لك أو لفرعك. عيّن الوردية من صفحة الموظف أو الفروع.',
            'shift_inactive' =>
              'الوردية المعيّنة غير نشطة. فعّلها من صفحة الورديات ثم احفظ.',
            'attendance_disabled' =>
              'الحضور غير مفعّل لهذا الموظف. فعّل «السماح بالحضور» من ملف الموظف.',
            'attendance_already_open' =>
              'تم تسجيل حضورك مسبقاً. لا يمكن تسجيل حضور ثانٍ قبل تسجيل الانصراف من الجلسة الحالية.',
            'qr_token_replayed' =>
              'تم استخدام رمز QR هذا من قبل. استخدم رمزاً جديداً أو سجّل عبر GPS.',
            'attendance_not_open' =>
              'لا توجد جلسة حضور مفتوحة لتسجيل الانصراف.',
            'attendance_period_closed' =>
              'انتهت فترة الوردية عن بُعد وأُغلقت. انتظر الوردية المجدولة التالية.',
            'checkout_too_early' =>
              'لا يمكن تسجيل الانصراف قبل نهاية فترة الوردية. استخدم الاستئذان المعتمد عند الحاجة إلى خروج مبكر.',
            'invalid_access_token' =>
              'انتهت جلسة الدخول. سجّل الخروج ثم ادخل مرة أخرى.',
            'shift_not_working_today' => 'لا توجد وردية مجدولة لهذا اليوم.',
            'subscription_inactive' =>
              'الاشتراك غير نشط، لذلك لا يمكن تسجيل الحضور.',
            'company_inactive' =>
              'حساب الشركة غير نشط، لذلك لا يمكن تسجيل الحضور.',
            'wifi_not_configured' =>
              'لم يضف المسؤول شبكة Wi‑Fi معتمدة لهذا الفرع بعد.',
            'wifi_network_not_authorized' =>
              'شبكة Wi‑Fi الحالية غير معتمدة لهذا الفرع. اتصل بشبكة الفرع ثم أعد المحاولة.',
            _ => null,
          };
          if (localized != null) return localized;
        } else {
          final localized = switch (code) {
            'wifi_not_configured' =>
              'The administrator has not configured an authorized Wi‑Fi network for this branch.',
            'wifi_network_not_authorized' =>
              'The current Wi‑Fi network is not authorized for this branch. Connect to the branch network and retry.',
            'attendance_period_closed' =>
              'This remote shift period is closed. Wait for the next scheduled period.',
            _ => null,
          };
          if (localized != null) return localized;
        }
        if (data['detail'] is String) return data['detail'] as String;
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

  Future<void> _reviewGeofenceExit(
    GeofenceExitEvent event,
    String decision,
  ) async {
    final controller = TextEditingController();
    final comment = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(_ar ? 'سبب قرار المراجعة' : 'Review decision reason'),
        content: TextField(
          controller: controller,
          minLines: 2,
          maxLines: 4,
          maxLength: 2000,
          autofocus: true,
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: Text(_ar ? 'إلغاء' : 'Cancel'),
          ),
          FilledButton(
            onPressed: () {
              if (controller.text.trim().length >= 3) {
                Navigator.of(dialogContext).pop(controller.text.trim());
              }
            },
            child: Text(_ar ? 'حفظ' : 'Save'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (comment == null || !mounted) return;
    setState(() => _submitting = true);
    try {
      await ref
          .read(attendanceApiProvider)
          .reviewGeofenceExit(
            session: widget.session,
            eventId: event.id,
            version: event.version,
            decision: decision,
            comment: comment,
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
    final permissionReturn = _permissionReturnRecord;
    final returningFromPermission = permissionReturn != null;
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
                      ? returningFromPermission
                            ? 'خرجت باستئذان معتمد. أثبت عودتك لاستكمال الدوام.'
                            : 'لا توجد جلسة حضور مفتوحة.'
                      : returningFromPermission
                      ? 'You checked out with approved permission. Record your return to continue.'
                      : 'No attendance session is open.')
                : (_ar
                      ? 'أنت مسجل حضور حاليًا.'
                      : 'You are currently checked in.'),
          ),
          if (!widget.managerMode) ...<Widget>[
            const SizedBox(height: 10),
            Card(
              child: ListTile(
                leading: const Icon(Icons.fingerprint_rounded),
                title: Text(
                  _biometricPolicy == 'required'
                      ? (_ar
                            ? 'البصمة مطلوبة للحضور'
                            : 'Biometrics required for attendance')
                      : _biometricPolicy == 'disabled'
                      ? (_ar
                            ? 'البصمة معطلة بسياسة الشركة'
                            : 'Biometrics disabled by company policy')
                      : (_ar
                            ? 'البصمة اختيارية عند توفرها'
                            : 'Biometrics optional when available'),
                ),
                subtitle: _lastBiometricResult == null
                    ? null
                    : Text(_biometricMessage(_lastBiometricResult!)),
              ),
            ),
          ],
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
              onPressed: _submitting || (open != null && !_checkoutAllowed)
                  ? null
                  : () => _submit(method: 'gps'),
              style: open == null
                  ? null
                  : FilledButton.styleFrom(
                      backgroundColor: Colors.amber.shade600,
                      foregroundColor: Colors.black,
                    ),
              icon: Icon(
                open == null ? Icons.login_rounded : Icons.logout_rounded,
              ),
              label: Text(
                open == null
                    ? (_ar
                          ? returningFromPermission
                                ? 'إثبات العودة من الاستئذان عبر GPS'
                                : 'تسجيل حضور عبر GPS'
                          : returningFromPermission
                          ? 'Record return with GPS'
                          : 'Check in with GPS')
                    : (_ar ? 'تسجيل انصراف عبر GPS' : 'Check out with GPS'),
              ),
            ),
            if (returningFromPermission) ...<Widget>[
              const SizedBox(height: 6),
              Text(
                _ar
                    ? 'سيُغلق الاستئذان عند إثبات العودة، ويُسجّل التأخير إن تجاوزت وقت الرجوع.'
                    : 'The permission ends when you record your return; a late return is recorded when applicable.',
                textAlign: TextAlign.center,
              ),
            ],
            if (open != null && !_checkoutAllowed) ...<Widget>[
              const SizedBox(height: 6),
              Text(
                _ar
                    ? 'سيُتاح الانصراف بعد نهاية فترة الوردية.'
                    : 'Check-out will be available after the scheduled period ends.',
                textAlign: TextAlign.center,
              ),
            ],
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: _submitting || (open != null && !_checkoutAllowed)
                  ? null
                  : () => _submit(method: 'wifi'),
              icon: const Icon(Icons.wifi_rounded),
              label: Text(
                open == null
                    ? (_ar
                          ? returningFromPermission
                                ? 'إثبات العودة عبر Wi‑Fi'
                                : 'تسجيل حضور عبر Wi‑Fi'
                          : returningFromPermission
                          ? 'Record return with Wi‑Fi'
                          : 'Check in with Wi‑Fi')
                    : (_ar ? 'تسجيل انصراف عبر Wi‑Fi' : 'Check out with Wi‑Fi'),
              ),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: _submitting || (open != null && !_checkoutAllowed)
                  ? null
                  : _scanQr,
              icon: const Icon(Icons.qr_code_scanner_rounded),
              label: Text(_ar ? 'مسح رمز QR' : 'Scan branch QR'),
            ),
          ],
          if (_lastDistance != null)
            Text(
              '${_ar ? 'المسافة عن الفرع' : 'Distance from branch'}: $_lastDistance m',
            ),
          if (widget.managerMode &&
              widget.session.can('geofence_exits:view')) ...<Widget>[
            const SizedBox(height: 24),
            Text(
              _ar ? 'نوع سجل المتابعة' : 'Attendance monitoring view',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            SegmentedButton<int>(
              segments: <ButtonSegment<int>>[
                ButtonSegment<int>(
                  value: 0,
                  icon: const Icon(Icons.fingerprint_rounded),
                  label: Text(_ar ? 'الحضور والانصراف' : 'Attendance'),
                ),
                ButtonSegment<int>(
                  value: 1,
                  icon: const Icon(Icons.location_searching_rounded),
                  label: Text(_ar ? 'تحقق النطاق' : 'Geofence checks'),
                ),
              ],
              selected: <int>{_managerAttendanceTab},
              onSelectionChanged: (selection) =>
                  setState(() => _managerAttendanceTab = selection.first),
            ),
          ],
          if (widget.managerMode &&
              widget.session.can('geofence_exits:view') &&
              _managerAttendanceTab == 1) ...<Widget>[
            const SizedBox(height: 28),
            Text(
              _ar ? 'مراجعة مغادرة النطاق' : 'Geofence exit review',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 10),
            if (_geofenceExits.isEmpty)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Text(
                    _ar
                        ? 'لا توجد أحداث للمراجعة.'
                        : 'No exit events to review.',
                  ),
                ),
              ),
            ..._geofenceExits.map(
              (event) => Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      Text(
                        event.employeeName ??
                            (_ar ? 'موظف غير مسمى' : 'Unnamed employee'),
                        style: Theme.of(context).textTheme.titleMedium
                            ?.copyWith(fontWeight: FontWeight.w800),
                      ),
                      Text(
                        _geofenceStatusLabel(event.status),
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                      Text(
                        '${_ar ? 'وقت التحقق' : 'Detected'}: ${_formatDateTime(event.detectedAt)}',
                      ),
                      Text(
                        event.distanceM == null
                            ? (_ar
                                  ? 'المسافة غير متاحة'
                                  : 'Distance unavailable')
                            : '${_ar ? 'المسافة عن الفرع' : 'Distance from branch'}: ${event.distanceM}${_ar ? ' مترًا' : ' m'}',
                      ),
                      if (event.reviewComment != null)
                        Text(event.reviewComment!)
                      else if (event.requiresReview &&
                          widget.session.can('geofence_exits:manage'))
                        Wrap(
                          spacing: 8,
                          children: <Widget>[
                            TextButton(
                              onPressed: _submitting
                                  ? null
                                  : () => _reviewGeofenceExit(
                                      event,
                                      'confirmed_unauthorized',
                                    ),
                              child: Text(_ar ? 'تأكيد المخالفة' : 'Confirm'),
                            ),
                            TextButton(
                              onPressed: _submitting
                                  ? null
                                  : () =>
                                        _reviewGeofenceExit(event, 'dismissed'),
                              child: Text(_ar ? 'استبعاد' : 'Dismiss'),
                            ),
                            TextButton(
                              onPressed: _submitting
                                  ? null
                                  : () => _reviewGeofenceExit(
                                      event,
                                      'approved_exception',
                                    ),
                              child: Text(
                                _ar ? 'استثناء معتمد' : 'Approve exception',
                              ),
                            ),
                          ],
                        ),
                      ExpansionTile(
                        tilePadding: EdgeInsets.zero,
                        title: Text(_ar ? 'تفاصيل تقنية' : 'Technical details'),
                        children: <Widget>[
                          Align(
                            alignment: AlignmentDirectional.centerStart,
                            child: Text(
                              '${_ar ? 'عدد قراءات التحقق' : 'Verification samples'}: ${event.samples}\n'
                              '${_ar ? 'الموظف' : 'Employee'}: ${event.employeeName ?? (_ar ? 'موظف غير مسمى' : 'Unnamed employee')}',
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
          if (widget.managerMode && _managerAttendanceTab == 0) ...<Widget>[
            const SizedBox(height: 24),
            _ManagerAttendanceRoster(
              records: _records,
              arabic: _ar,
              statusLabel: _attendanceStatusLabel,
            ),
          ],
          if (!widget.managerMode || _managerAttendanceTab == 0) ...<Widget>[
            const SizedBox(height: 28),
            Text(
              widget.managerMode
                  ? (_ar ? 'السجل التفصيلي' : 'Detailed history')
                  : (_ar ? 'السجل الأخير' : 'Recent history'),
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
                      title: Text(
                        '${record.workDate} · ${_attendanceStatusLabel(record.status)}',
                      ),
                      subtitle: Text(
                        '${_ar ? 'ساعات العمل' : 'Worked'}: '
                        '${_workedDurationLabel(record.workedMinutes)} · '
                        '${_ar ? 'التأخير' : 'Late'}: '
                        '${_ar ? '${record.lateMinutes} دقيقة' : '${record.lateMinutes}m'}',
                      ),
                      trailing: IconButton(
                        tooltip: _ar
                            ? 'عرض الموقع على الخريطة'
                            : 'View location on map',
                        onPressed: () => _showLocationMap(record),
                        icon: const Icon(Icons.location_on_outlined),
                      ),
                    ),
                  ),
                ),
          ],
        ],
      ),
    );
  }

  String _geofenceStatusLabel(String status) {
    return switch (status) {
      'inside' => _ar ? 'داخل نطاق الفرع' : 'Inside branch range',
      'observing' => _ar ? 'جاري التحقق' : 'Checking location',
      'unauthorized' => _ar ? 'مغادرة غير مصرح بها' : 'Unauthorized exit',
      'confirmed_unauthorized' => _ar ? 'مخالفة مؤكدة' : 'Confirmed violation',
      'approved_exit' => _ar ? 'خروج بإذن معتمد' : 'Approved permission',
      'approved_exception' => _ar ? 'استثناء معتمد' : 'Approved exception',
      'dismissed' => _ar ? 'تم تجاهل الحالة' : 'Dismissed',
      'reconfirmed' => _ar ? 'عاد إلى النطاق' : 'Back inside range',
      _ => _ar ? 'حالة غير معروفة' : 'Unknown status',
    };
  }

  String _workedDurationLabel(int minutes) {
    final hours = minutes ~/ 60;
    final remainder = minutes % 60;
    if (!_ar) return '${hours}h ${remainder}m';
    if (hours == 0) return '$remainder دقيقة';
    if (remainder == 0) return '$hours ساعة';
    return '$hours ساعة و$remainder دقيقة';
  }

  String _attendanceStatusLabel(String status) {
    return switch (status) {
      'on_time' => _ar ? 'حاضر في الوقت' : 'On time',
      'late' => _ar ? 'متأخر' : 'Late',
      'on_permission' => _ar ? 'مستأذن' : 'On permission',
      'permission_return_late' =>
        _ar ? 'عاد متأخرًا من الاستئذان' : 'Late return from permission',
      'absent' => _ar ? 'غائب' : 'Absent',
      'on_leave' => _ar ? 'إجازة معتمدة' : 'Approved leave',
      'missing_check_out' => _ar ? 'لم يسجل الانصراف' : 'Missing check-out',
      _ => _ar ? 'قيد المراجعة' : 'Pending review',
    };
  }

  String _formatDateTime(DateTime? value) {
    if (value == null) return '—';
    final local = value.toLocal();
    final date = MaterialLocalizations.of(context).formatMediumDate(local);
    final time = MaterialLocalizations.of(
      context,
    ).formatTimeOfDay(TimeOfDay.fromDateTime(local));
    return '$date، $time';
  }
}

class _ManagerAttendanceRoster extends StatelessWidget {
  const _ManagerAttendanceRoster({
    required this.records,
    required this.arabic,
    required this.statusLabel,
  });

  final List<AttendanceRecord> records;
  final bool arabic;
  final String Function(String status) statusLabel;

  String _time(DateTime? value) {
    if (value == null) return '—';
    final local = value.toLocal();
    final hour = local.hour.toString().padLeft(2, '0');
    final minute = local.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now().toIso8601String().substring(0, 10);
    final todayRecords = records
        .where((item) => item.workDate == today)
        .toList();
    final shown = todayRecords.isNotEmpty
        ? todayRecords
        : records.take(20).toList();
    final present = shown.where((item) => item.checkedInAt != null).length;
    final open = shown.where((item) => item.isOpen).length;
    final absent = shown.where((item) => item.status == 'absent').length;
    final title = todayRecords.isNotEmpty
        ? (arabic ? 'حضور اليوم · $today' : 'Today\'s attendance · $today')
        : (arabic ? 'آخر سجلات الحضور' : 'Latest attendance records');
    return Card(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 16, 14, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(
              title,
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 6),
            Text(
              arabic
                  ? 'الحاضرون: $present · جلسات مفتوحة: $open · الغائبون: $absent'
                  : 'Checked in: $present · Open sessions: $open · Absent: $absent',
            ),
            const SizedBox(height: 12),
            if (shown.isEmpty)
              Text(
                arabic
                    ? 'لا توجد سجلات لهذا اليوم.'
                    : 'No records for this day.',
              )
            else
              ...shown.map(
                (record) => Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surface,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: Theme.of(context).colorScheme.outlineVariant,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: Text(
                              record.employeeName ??
                                  record.employeeEmail ??
                                  (arabic
                                      ? 'موظف غير معروف'
                                      : 'Unknown employee'),
                              style: Theme.of(context).textTheme.titleMedium
                                  ?.copyWith(fontWeight: FontWeight.w700),
                            ),
                          ),
                          Chip(label: Text(statusLabel(record.status))),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${arabic ? 'الفرع' : 'Branch'}: ${record.branchName ?? '—'}'
                        ' · ${arabic ? 'الوردية' : 'Shift'}: ${record.shiftName ?? '—'}',
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${arabic ? 'الحضور' : 'Check-in'}: ${_time(record.checkedInAt)}'
                        ' · ${arabic ? 'الانصراف' : 'Check-out'}: ${_time(record.checkedOutAt)}',
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _AttendanceLocationMapSheet extends StatelessWidget {
  const _AttendanceLocationMapSheet({
    required this.events,
    required this.arabic,
    required this.recordDate,
  });

  final List<AttendanceLocationEvent> events;
  final bool arabic;
  final String recordDate;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(theme.colorScheme.surface)
      ..loadHtmlString(_mapHtml());
    final branch = events.first;
    return SafeArea(
      child: Container(
        height: MediaQuery.sizeOf(context).height * .86,
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 14, 12, 8),
              child: Row(
                children: <Widget>[
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primaryContainer,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      Icons.map_rounded,
                      color: theme.colorScheme.onPrimaryContainer,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          arabic ? 'موقع تسجيل الحضور' : 'Attendance location',
                          style: theme.textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        Text(
                          '${branch.employeeName ?? (arabic ? 'الموظف' : 'Employee')} · ${arabic ? 'السجل' : 'Record'} $recordDate',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: theme.textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: arabic ? 'إغلاق' : 'Close',
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close_rounded),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  _MapLegendChip(
                    color: Colors.teal,
                    label: arabic ? 'موقع الموظف' : 'Employee location',
                  ),
                  _MapLegendChip(
                    color: Colors.indigo,
                    label: arabic ? 'الفرع' : 'Branch',
                  ),
                  _MapLegendChip(
                    color: Colors.indigo.withValues(alpha: .22),
                    label: arabic ? 'نطاق الحضور' : 'Attendance radius',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: WebViewWidget(controller: controller),
                ),
              ),
            ),
            SizedBox(
              height: 132,
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
                scrollDirection: Axis.horizontal,
                itemCount: events.length,
                separatorBuilder: (_, _) => const SizedBox(width: 10),
                itemBuilder: (context, index) {
                  final event = events[index];
                  final isCheckIn = event.eventType == 'check_in';
                  return SizedBox(
                    width: 220,
                    child: Card(
                      margin: EdgeInsets.zero,
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Row(
                              children: <Widget>[
                                Icon(
                                  isCheckIn
                                      ? Icons.login_rounded
                                      : Icons.logout_rounded,
                                  size: 18,
                                  color: isCheckIn
                                      ? Colors.teal
                                      : Colors.amber.shade800,
                                ),
                                const SizedBox(width: 6),
                                Text(
                                  isCheckIn
                                      ? (arabic ? 'الحضور' : 'Check-in')
                                      : (arabic ? 'الانصراف' : 'Check-out'),
                                  style: theme.textTheme.titleSmall?.copyWith(
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            Text(_eventTime(context, event.occurredAt)),
                            Text(
                              event.distanceM == null
                                  ? (arabic
                                        ? 'المسافة غير متاحة'
                                        : 'Distance unavailable')
                                  : '${arabic ? 'المسافة' : 'Distance'}: ${event.distanceM} ${arabic ? 'م' : 'm'}',
                              style: theme.textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _eventTime(BuildContext context, DateTime? value) {
    if (value == null) return '—';
    final local = value.toLocal();
    final date = MaterialLocalizations.of(context).formatMediumDate(local);
    final time = MaterialLocalizations.of(
      context,
    ).formatTimeOfDay(TimeOfDay.fromDateTime(local));
    return '$date، $time';
  }

  String _mapHtml() {
    final branch = events.first;
    final points = events
        .map(
          (event) => <String, Object?>{
            'lat': event.latitude,
            'lng': event.longitude,
            'event': event.eventType,
            'time': event.occurredAt?.toLocal().toIso8601String(),
            'distance': event.distanceM,
          },
        )
        .toList(growable: false);
    final branchData = <String, Object?>{
      'lat': branch.branchLatitude,
      'lng': branch.branchLongitude,
      'name': branch.branchName,
      'radius': branch.geofenceRadiusM,
    };
    final pointJson = jsonEncode(points);
    final branchJson = jsonEncode(branchData);
    final direction = arabic ? 'rtl' : 'ltr';
    final employeeLabel = arabic ? 'موقع الموظف' : 'Employee location';
    final branchLabel = arabic ? 'الفرع' : 'Branch';
    final radiusLabel = arabic ? 'نطاق الحضور' : 'Attendance radius';
    final checkInLabel = arabic ? 'الحضور' : 'Check-in';
    final checkOutLabel = arabic ? 'الانصراف' : 'Check-out';
    final distanceLabel = arabic ? 'المسافة' : 'Distance';
    return '''
<!doctype html>
<html lang="${arabic ? 'ar' : 'en'}" dir="$direction">
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="" />
<style>
html, body, #map { height: 100%; width: 100%; margin: 0; background: #e8f2f1; }
body { overflow: hidden; overscroll-behavior: none; touch-action: none; -webkit-tap-highlight-color: transparent; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
#map { touch-action: pan-x pan-y; }
.leaflet-control-zoom a { color: #115e59 !important; font-weight: 800; }
.leaflet-control-attribution { font-size: 9px; }
.pin { border-radius: 999px; border: 3px solid white; box-shadow: 0 3px 12px rgba(15, 23, 42, .35); }
.pin.employee { background: #0f766e; width: 18px; height: 18px; }
.pin.branch { background: #3730a3; width: 18px; height: 18px; }
.leaflet-popup-content-wrapper { border-radius: 14px; }
.leaflet-popup-content { margin: 12px 14px; font-size: 13px; line-height: 1.6; }
</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<script>
const points = $pointJson;
const branch = $branchJson;
const map = L.map('map', {
  zoomControl: false,
  preferCanvas: true,
  zoomAnimation: true,
  fadeAnimation: true,
  markerZoomAnimation: false,
  zoomSnap: 0.25,
  zoomDelta: 0.5,
  inertia: true,
  inertiaDeceleration: 2800,
  easeLinearity: 0.22,
  tap: true,
  tapTolerance: 18
});
L.control.zoom({ position: '${arabic ? 'topleft' : 'topright'}' }).addTo(map);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const employeeIcon = L.divIcon({ className: 'pin employee', iconSize: [24, 24], iconAnchor: [12, 12] });
const branchIcon = L.divIcon({ className: 'pin branch', iconSize: [24, 24], iconAnchor: [12, 12] });
const bounds = [[branch.lat, branch.lng]];
L.marker([branch.lat, branch.lng], { icon: branchIcon }).addTo(map)
  .bindPopup('<strong>$branchLabel</strong><br>' + escapeHtml(branch.name));
L.circle([branch.lat, branch.lng], {
  radius: branch.radius,
  color: '#3730a3',
  fillColor: '#6366f1',
  fillOpacity: 0.13,
  weight: 2
}).addTo(map).bindTooltip('$radiusLabel: ' + branch.radius + ' m');
points.forEach((point, index) => {
  if (point.lat == null || point.lng == null) return;
  bounds.push([point.lat, point.lng]);
  const isIn = point.event === 'check_in';
  const label = isIn ? '$checkInLabel' : '$checkOutLabel';
  const distance = point.distance == null ? '—' : point.distance + ' m';
  L.marker([point.lat, point.lng], { icon: employeeIcon }).addTo(map)
    .bindPopup('<strong>$employeeLabel · ' + label + '</strong><br>$distanceLabel: ' + escapeHtml(distance));
});
map.fitBounds(bounds, { padding: [34, 34], maxZoom: 17 });
</script>
</body>
</html>
''';
  }
}

class _MapLegendChip extends StatelessWidget {
  const _MapLegendChip({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) => Chip(
    avatar: CircleAvatar(backgroundColor: color, radius: 6),
    label: Text(label),
    visualDensity: VisualDensity.compact,
  );
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
