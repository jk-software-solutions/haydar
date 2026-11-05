import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../auth/application/auth_api.dart';

final subscriptionApiProvider = Provider<SubscriptionApi>(
  (ref) => SubscriptionApi(ref.watch(dioProvider)),
);

class SubscriptionApi {
  SubscriptionApi(this.dio);

  final Dio dio;

  Future<List<SubscriptionPlan>> plans() async {
    final response = await dio.get<List<dynamic>>('/billing/plans');
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(SubscriptionPlan.fromJson)
        .toList(growable: false);
  }

  Future<CompanySubscription?> current() async {
    final response = await dio.get<dynamic>('/billing/subscription');
    if (response.data == null) return null;
    return CompanySubscription.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<SubscriptionRequest>> requests() async {
    final response = await dio.get<List<dynamic>>(
      '/billing/subscription-requests',
    );
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(SubscriptionRequest.fromJson)
        .toList(growable: false);
  }

  Future<SubscriptionRequest> request({
    required AuthSession session,
    required String planId,
    required String billingCycle,
    String? couponCode,
    String? note,
  }) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/billing/subscription-requests',
      data: <String, dynamic>{
        'plan_id': planId,
        'billing_cycle': billingCycle,
        if (couponCode != null && couponCode.trim().isNotEmpty)
          'coupon_code': couponCode.trim(),
        if (note != null && note.trim().isNotEmpty) 'note': note.trim(),
      },
    );
    return SubscriptionRequest.fromJson(response.data ?? <String, dynamic>{});
  }
}

class SubscriptionPlan {
  const SubscriptionPlan({
    required this.id,
    required this.code,
    required this.name,
    required this.description,
    required this.monthlyPrice,
    required this.annualPrice,
    required this.currency,
    required this.limits,
    required this.features,
    required this.supportLevel,
  });

  factory SubscriptionPlan.fromJson(Map<String, dynamic> json) {
    return SubscriptionPlan(
      id: '${json['id'] ?? ''}',
      code: '${json['code'] ?? ''}',
      name: '${json['name'] ?? ''}',
      description: '${json['description'] ?? ''}',
      monthlyPrice: _number(json['monthly_price']),
      annualPrice: _number(json['annual_price']),
      currency: '${json['currency'] ?? 'SAR'}',
      limits: _map(json['limits']),
      features: _map(json['features']),
      supportLevel: '${json['support_level'] ?? ''}',
    );
  }

  final String id;
  final String code;
  final String name;
  final String description;
  final int monthlyPrice;
  final int annualPrice;
  final String currency;
  final Map<String, dynamic> limits;
  final Map<String, dynamic> features;
  final String supportLevel;
}

class CompanySubscription {
  const CompanySubscription({
    required this.plan,
    required this.billingCycle,
    required this.status,
    required this.startsAt,
    required this.endsAt,
  });

  factory CompanySubscription.fromJson(Map<String, dynamic> json) {
    return CompanySubscription(
      plan: SubscriptionPlan.fromJson(
        (json['plan'] as Map<String, dynamic>?) ?? <String, dynamic>{},
      ),
      billingCycle: '${json['billing_cycle'] ?? ''}',
      status: '${json['status'] ?? ''}',
      startsAt: DateTime.tryParse('${json['starts_at'] ?? ''}'),
      endsAt: DateTime.tryParse('${json['ends_at'] ?? ''}'),
    );
  }

  final SubscriptionPlan plan;
  final String billingCycle;
  final String status;
  final DateTime? startsAt;
  final DateTime? endsAt;
}

class SubscriptionRequest {
  const SubscriptionRequest({
    required this.id,
    required this.plan,
    required this.billingCycle,
    required this.status,
    required this.couponCode,
    required this.note,
    required this.reviewNote,
    required this.createdAt,
  });

  factory SubscriptionRequest.fromJson(Map<String, dynamic> json) {
    return SubscriptionRequest(
      id: '${json['id'] ?? ''}',
      plan: SubscriptionPlan.fromJson(
        (json['plan'] as Map<String, dynamic>?) ?? <String, dynamic>{},
      ),
      billingCycle: '${json['billing_cycle'] ?? ''}',
      status: '${json['status'] ?? ''}',
      couponCode: json['coupon_code'] as String?,
      note: json['note'] as String?,
      reviewNote: json['review_note'] as String?,
      createdAt: DateTime.tryParse('${json['created_at'] ?? ''}'),
    );
  }

  final String id;
  final SubscriptionPlan plan;
  final String billingCycle;
  final String status;
  final String? couponCode;
  final String? note;
  final String? reviewNote;
  final DateTime? createdAt;
}

int _number(Object? value) =>
    value is num ? value.toInt() : int.tryParse('$value') ?? 0;

Map<String, dynamic> _map(Object? value) {
  final map = value is Map ? value : const <dynamic, dynamic>{};
  return map.map((key, value) => MapEntry('$key', value));
}
