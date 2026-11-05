import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart' as intl;

import '../../../l10n/generated/app_localizations.dart';
import '../../auth/application/auth_api.dart';
import '../application/subscription_api.dart';

class SubscriptionScreen extends ConsumerStatefulWidget {
  const SubscriptionScreen({required this.session, super.key});

  final AuthSession session;

  @override
  ConsumerState<SubscriptionScreen> createState() => _SubscriptionScreenState();
}

class _SubscriptionScreenState extends ConsumerState<SubscriptionScreen> {
  final TextEditingController _couponController = TextEditingController();
  final TextEditingController _noteController = TextEditingController();
  List<SubscriptionPlan> _plans = const <SubscriptionPlan>[];
  List<SubscriptionRequest> _requests = const <SubscriptionRequest>[];
  CompanySubscription? _current;
  String? _selectedPlanId;
  String _billingCycle = 'monthly';
  String? _error;
  bool _loading = true;
  bool _submitting = false;

  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';
  bool get _canManage =>
      widget.session.can('subscription:manage') ||
      widget.session.roles.contains('OWNER');

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _couponController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (mounted) setState(() => _loading = true);
    try {
      final api = ref.read(subscriptionApiProvider);
      final values = await Future.wait<dynamic>(<Future<dynamic>>[
        api.plans(),
        api.current(),
        api.requests(),
      ]);
      if (!mounted) return;
      final plans = values[0] as List<SubscriptionPlan>;
      setState(() {
        _plans = plans;
        _current = values[1] as CompanySubscription?;
        _requests = values[2] as List<SubscriptionRequest>;
        _selectedPlanId =
            _selectedPlanId != null &&
                plans.any((plan) => plan.id == _selectedPlanId)
            ? _selectedPlanId
            : (plans.isEmpty ? null : plans.first.id);
        _error = null;
        _loading = false;
      });
    } on Object catch (error) {
      if (mounted) {
        setState(() {
          _error = _message(error);
          _loading = false;
        });
      }
    }
  }

  Future<void> _submitRequest() async {
    final planId = _selectedPlanId;
    if (!_canManage || _submitting || planId == null) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await ref
          .read(subscriptionApiProvider)
          .request(
            session: widget.session,
            planId: planId,
            billingCycle: _billingCycle,
            couponCode: _couponController.text,
            note: _noteController.text,
          );
      if (!mounted) return;
      _couponController.clear();
      _noteController.clear();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _ar
                ? 'تم إرسال طلب الاشتراك. سيعتمده مالك المنصة.'
                : 'Subscription request sent. The platform owner will review it.',
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
      await _load();
    } on Object catch (error) {
      if (mounted) setState(() => _error = _message(error));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.subscriptionTitle),
        actions: <Widget>[
          IconButton(
            tooltip: l10n.retryButton,
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: _loading && _plans.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(18, 16, 18, 32),
                children: <Widget>[
                  _HeroCard(session: widget.session),
                  const SizedBox(height: 16),
                  if (_error != null) ...<Widget>[
                    _NoticeCard(
                      icon: Icons.error_outline_rounded,
                      message: _error!,
                      color: Theme.of(context).colorScheme.errorContainer,
                    ),
                    const SizedBox(height: 12),
                  ],
                  if (_current != null) ...<Widget>[
                    _CurrentSubscriptionCard(subscription: _current!),
                    const SizedBox(height: 16),
                  ] else ...<Widget>[
                    _NoticeCard(
                      icon: Icons.info_outline_rounded,
                      message: l10n.subscriptionNoActive,
                      color: Theme.of(context).colorScheme.secondaryContainer,
                    ),
                    const SizedBox(height: 16),
                  ],
                  _SectionTitle(
                    title: l10n.subscriptionPlans,
                    subtitle: l10n.subscriptionDescription,
                  ),
                  const SizedBox(height: 10),
                  ..._plans.asMap().entries.map(
                    (entry) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _PlanCard(
                        plan: entry.value,
                        selected: entry.value.id == _selectedPlanId,
                        featured: entry.key == (_plans.length > 1 ? 1 : 0),
                        billingCycle: _billingCycle,
                        onTap: _canManage
                            ? () => setState(
                                () => _selectedPlanId = entry.value.id,
                              )
                            : null,
                      ),
                    ),
                  ),
                  if (_plans.isEmpty)
                    _NoticeCard(
                      icon: Icons.inventory_2_outlined,
                      message: l10n.subscriptionNoPlans,
                      color: Theme.of(
                        context,
                      ).colorScheme.surfaceContainerHighest,
                    ),
                  const SizedBox(height: 8),
                  if (_canManage && _plans.isNotEmpty)
                    _RequestForm(
                      billingCycle: _billingCycle,
                      couponController: _couponController,
                      noteController: _noteController,
                      submitting: _submitting,
                      onCycleChanged: (value) =>
                          setState(() => _billingCycle = value),
                      onSubmit: _submitRequest,
                    )
                  else if (!_canManage)
                    _NoticeCard(
                      icon: Icons.lock_outline_rounded,
                      message: l10n.subscriptionViewOnly,
                      color: Theme.of(
                        context,
                      ).colorScheme.surfaceContainerHighest,
                    ),
                  const SizedBox(height: 20),
                  _SectionTitle(title: l10n.subscriptionRequests),
                  const SizedBox(height: 10),
                  if (_requests.isEmpty)
                    _NoticeCard(
                      icon: Icons.receipt_long_outlined,
                      message: l10n.subscriptionNoRequests,
                      color: Theme.of(
                        context,
                      ).colorScheme.surfaceContainerHighest,
                    )
                  else
                    ..._requests.map(
                      (request) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: _RequestHistoryCard(request: request),
                      ),
                    ),
                  const SizedBox(height: 8),
                  _NoticeCard(
                    icon: Icons.payments_outlined,
                    message: l10n.subscriptionManualActivation,
                    color: Theme.of(context).colorScheme.tertiaryContainer,
                  ),
                ],
              ),
            ),
    );
  }

  String _message(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['detail'] is String) {
        return data['detail'] as String;
      }
    }
    return _ar
        ? 'تعذر تحميل بيانات الاشتراك.'
        : 'Could not load subscription data.';
  }
}

class _HeroCard extends StatelessWidget {
  const _HeroCard({required this.session});

  final AuthSession session;

  @override
  Widget build(BuildContext context) {
    final ar = Localizations.localeOf(context).languageCode == 'ar';
    final scheme = Theme.of(context).colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: <Color>[scheme.primary, scheme.primaryContainer],
          begin: AlignmentDirectional.topStart,
          end: AlignmentDirectional.bottomEnd,
        ),
        borderRadius: BorderRadius.circular(26),
      ),
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Row(
          children: <Widget>[
            CircleAvatar(
              radius: 28,
              backgroundColor: Colors.white.withValues(alpha: .18),
              child: const Icon(
                Icons.workspace_premium_rounded,
                color: Colors.white,
                size: 32,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    ar ? 'اشتراك شركتك' : 'Your company subscription',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    session.companyName,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.white.withValues(alpha: .88),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, this.subtitle});

  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: <Widget>[
      Text(title, style: Theme.of(context).textTheme.headlineSmall),
      if (subtitle != null) ...<Widget>[
        const SizedBox(height: 3),
        Text(subtitle!, style: Theme.of(context).textTheme.bodyMedium),
      ],
    ],
  );
}

class _CurrentSubscriptionCard extends StatelessWidget {
  const _CurrentSubscriptionCard({required this.subscription});

  final CompanySubscription subscription;

  @override
  Widget build(BuildContext context) {
    final ar = Localizations.localeOf(context).languageCode == 'ar';
    final formatter = intl.DateFormat.yMMMd(
      Localizations.localeOf(context).toLanguageTag(),
    );
    final status = subscription.status == 'trial'
        ? (ar ? 'تجريبي' : 'Trial')
        : (ar ? 'نشط' : 'Active');
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                const Icon(Icons.verified_rounded),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    ar ? 'الاشتراك الحالي' : 'Current subscription',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                Chip(label: Text(status)),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              _planName(subscription.plan, ar),
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 6),
            Text(
              ar
                  ? 'ينتهي في ${subscription.endsAt == null ? 'غير محدد' : formatter.format(subscription.endsAt!)}'
                  : 'Ends ${subscription.endsAt == null ? 'indefinitely' : formatter.format(subscription.endsAt!)}',
            ),
          ],
        ),
      ),
    );
  }
}

class _PlanCard extends StatelessWidget {
  const _PlanCard({
    required this.plan,
    required this.selected,
    required this.featured,
    required this.billingCycle,
    required this.onTap,
  });

  final SubscriptionPlan plan;
  final bool selected;
  final bool featured;
  final String billingCycle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final ar = Localizations.localeOf(context).languageCode == 'ar';
    final scheme = Theme.of(context).colorScheme;
    final price = billingCycle == 'annual'
        ? plan.annualPrice
        : plan.monthlyPrice;
    final priceLabel = intl.NumberFormat.currency(
      locale: Localizations.localeOf(context).toLanguageTag(),
      symbol: plan.currency,
      decimalDigits: 2,
    ).format(price / 100);
    final limitEntries = plan.limits.entries.take(4).toList(growable: false);
    final featureEntries = plan.features.entries
        .where((entry) => entry.value == true || entry.value is String)
        .take(4)
        .toList(growable: false);
    return Card(
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(22),
        side: BorderSide(
          color: selected ? scheme.primary : scheme.outlineVariant,
          width: selected ? 2 : 1,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      _planName(plan, ar),
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  if (featured)
                    Chip(
                      avatar: const Icon(Icons.star_rounded, size: 16),
                      label: Text(ar ? 'الأكثر اختيارًا' : 'Popular'),
                    ),
                  if (selected)
                    Icon(Icons.check_circle_rounded, color: scheme.primary),
                ],
              ),
              if (_planDescription(plan, ar).isNotEmpty) ...<Widget>[
                const SizedBox(height: 5),
                Text(_planDescription(plan, ar)),
              ],
              const SizedBox(height: 14),
              Text(
                priceLabel,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  color: scheme.primary,
                  fontWeight: FontWeight.w900,
                ),
              ),
              Text(
                billingCycle == 'annual'
                    ? (ar ? 'للفترة السنوية' : 'per year')
                    : (ar ? 'للفترة الشهرية' : 'per month'),
              ),
              if (plan.supportLevel.isNotEmpty) ...<Widget>[
                const SizedBox(height: 4),
                Text(
                  '${ar ? 'الدعم' : 'Support'}: ${_supportLabel(plan.supportLevel, ar)}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              if (limitEntries.isNotEmpty) ...<Widget>[
                const SizedBox(height: 14),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: limitEntries
                      .map(
                        (entry) => Chip(
                          label: Text(
                            '${_limitLabel(entry.key, ar)}: ${entry.value}',
                          ),
                        ),
                      )
                      .toList(growable: false),
                ),
              ],
              if (featureEntries.isNotEmpty) ...<Widget>[
                const SizedBox(height: 10),
                ...featureEntries.map(
                  (entry) => Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(
                      children: <Widget>[
                        Icon(
                          Icons.check_rounded,
                          size: 18,
                          color: scheme.primary,
                        ),
                        const SizedBox(width: 6),
                        Expanded(child: Text(_featureLabel(entry, ar))),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _RequestForm extends StatelessWidget {
  const _RequestForm({
    required this.billingCycle,
    required this.couponController,
    required this.noteController,
    required this.submitting,
    required this.onCycleChanged,
    required this.onSubmit,
  });

  final String billingCycle;
  final TextEditingController couponController;
  final TextEditingController noteController;
  final bool submitting;
  final ValueChanged<String> onCycleChanged;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              l10n.subscriptionRequestTitle,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            SegmentedButton<String>(
              segments: <ButtonSegment<String>>[
                ButtonSegment(
                  value: 'monthly',
                  label: Text(l10n.subscriptionMonthly),
                ),
                ButtonSegment(
                  value: 'annual',
                  label: Text(l10n.subscriptionAnnual),
                ),
              ],
              selected: <String>{billingCycle},
              onSelectionChanged: (values) => onCycleChanged(values.first),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: couponController,
              textCapitalization: TextCapitalization.characters,
              decoration: InputDecoration(
                labelText: l10n.subscriptionCoupon,
                hintText: l10n.subscriptionCouponHint,
                prefixIcon: const Icon(Icons.discount_outlined),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: noteController,
              maxLines: 3,
              decoration: InputDecoration(
                labelText: l10n.subscriptionNote,
                hintText: l10n.subscriptionNoteHint,
                prefixIcon: const Icon(Icons.notes_rounded),
              ),
            ),
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: submitting ? null : onSubmit,
                icon: submitting
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.send_rounded),
                label: Text(
                  submitting
                      ? l10n.subscriptionSending
                      : l10n.subscriptionRequestButton,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RequestHistoryCard extends StatelessWidget {
  const _RequestHistoryCard({required this.request});

  final SubscriptionRequest request;

  @override
  Widget build(BuildContext context) {
    final ar = Localizations.localeOf(context).languageCode == 'ar';
    final status = switch (request.status) {
      'approved' => ar ? 'تمت الموافقة' : 'Approved',
      'rejected' => ar ? 'مرفوض' : 'Rejected',
      _ => ar ? 'قيد المراجعة' : 'Pending review',
    };
    final date = request.createdAt == null
        ? ''
        : intl.DateFormat.yMMMd(
            Localizations.localeOf(context).toLanguageTag(),
          ).format(request.createdAt!);
    return Card(
      child: ListTile(
        leading: const Icon(Icons.receipt_long_outlined),
        title: Text(_planName(request.plan, ar)),
        subtitle: Text(
          '${request.billingCycle == 'annual' ? (ar ? 'سنوي' : 'Annual') : (ar ? 'شهري' : 'Monthly')} · $date',
        ),
        trailing: Chip(label: Text(status)),
      ),
    );
  }
}

class _NoticeCard extends StatelessWidget {
  const _NoticeCard({
    required this.icon,
    required this.message,
    required this.color,
  });

  final IconData icon;
  final String message;
  final Color color;

  @override
  Widget build(BuildContext context) => Card(
    color: color,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: <Widget>[
          const Icon(Icons.info_outline_rounded),
          const SizedBox(width: 10),
          Expanded(child: Text(message)),
        ],
      ),
    ),
  );
}

String _limitLabel(String key, bool ar) {
  final normalized = key.toLowerCase();
  if (normalized.contains('employee')) return ar ? 'الموظفون' : 'Employees';
  if (normalized.contains('branch')) return ar ? 'الفروع' : 'Branches';
  if (normalized.contains('storage')) return ar ? 'التخزين' : 'Storage';
  return key;
}

String _featureLabel(MapEntry<String, dynamic> entry, bool ar) {
  final featureLabels = <String, String>{
    'qr': ar ? 'رمز QR' : 'QR codes',
    'gps': ar ? 'الحضور عبر GPS' : 'GPS attendance',
    'wifi': ar ? 'التحقق عبر Wi‑Fi' : 'Wi‑Fi verification',
    'tasks': ar ? 'المهام' : 'Tasks',
    'reports': ar ? 'التقارير' : 'Reports',
    'documents': ar ? 'المرفقات والوثائق' : 'Documents and attachments',
  };
  final known = featureLabels[entry.key.toLowerCase()];
  if (known != null) {
    final value = entry.value;
    if (value is String && value.isNotEmpty) {
      final localizedValue = ar
          ? switch (value.toLowerCase()) {
              'basic' => 'أساسي',
              'advanced' => 'متقدم',
              _ => value,
            }
          : value;
      return '$known: $localizedValue';
    }
    return known;
  }
  final key = entry.key.replaceAll('_', ' ');
  final value = entry.value;
  if (value is String && value.isNotEmpty) return value;
  return ar ? 'يشمل $key' : key;
}

String _planName(SubscriptionPlan plan, bool ar) {
  if (!ar) return plan.name;
  return switch (plan.code.toUpperCase()) {
    'FREE_TRIAL' => 'تجربة مجانية',
    'BASIC' => 'الأساسية',
    'PROFESSIONAL' => 'الاحترافية',
    'ENTERPRISE' => 'المؤسسات',
    _ => plan.name,
  };
}

String _planDescription(SubscriptionPlan plan, bool ar) {
  if (!ar) return plan.description;
  return switch (plan.code.toUpperCase()) {
    'FREE_TRIAL' => 'باقة للتجربة والتقييم',
    'BASIC' => 'للشركات والفرق الصغيرة',
    'PROFESSIONAL' => 'للمنشآت المتنامية',
    'ENTERPRISE' => 'باقة مخصصة للمؤسسات',
    _ => plan.description,
  };
}

String _supportLabel(String value, bool ar) {
  if (!ar) return value;
  return switch (value.toLowerCase()) {
    'community' => 'مجتمعي',
    'standard' => 'قياسي',
    'priority' => 'أولوية',
    'dedicated' => 'مخصص',
    _ => value,
  };
}
