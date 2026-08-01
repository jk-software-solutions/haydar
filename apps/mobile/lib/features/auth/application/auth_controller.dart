import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_api.dart';

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>(
  (ref) {
    return AuthController(ref.watch(authApiProvider));
  },
);

class AuthState {
  const AuthState({
    required this.isInitializing,
    required this.isSubmitting,
    this.session,
    this.error,
  });

  const AuthState.initial()
    : isInitializing = true,
      isSubmitting = false,
      session = null,
      error = null;

  const AuthState.signedOut({this.error})
    : isInitializing = false,
      isSubmitting = false,
      session = null;

  const AuthState.authenticated(this.session)
    : isInitializing = false,
      isSubmitting = false,
      error = null;

  final bool isInitializing;
  final bool isSubmitting;
  final AuthSession? session;
  final Object? error;

  AuthState copyWith({
    bool? isInitializing,
    bool? isSubmitting,
    AuthSession? session,
    Object? error,
    bool clearError = false,
  }) {
    return AuthState(
      isInitializing: isInitializing ?? this.isInitializing,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      session: session ?? this.session,
      error: clearError ? null : error ?? this.error,
    );
  }
}

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._api) : super(const AuthState.initial()) {
    _restore();
  }

  AuthController.forTest(super.state) : _api = null;

  final AuthApi? _api;

  Future<void> _restore() async {
    try {
      final session = await _api!.restoreSession();
      if (session == null) {
        state = const AuthState.signedOut();
      } else {
        state = AuthState.authenticated(session);
      }
    } on Object catch (error) {
      state = AuthState.signedOut(error: error);
    }
  }

  Future<AuthSession> signIn({
    required String email,
    required String password,
  }) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      final session = await _api!.login(email: email, password: password);
      state = AuthState.authenticated(session);
      return session;
    } on Object catch (error) {
      state = AuthState.signedOut(error: error);
      rethrow;
    }
  }

  Future<void> signOut() async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      await _api!.logout();
      state = const AuthState.signedOut();
    } on Object catch (error) {
      state = AuthState.signedOut(error: error);
      rethrow;
    }
  }

  String friendlyError(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map<String, dynamic>) {
        final detail = data['detail'];
        if (detail is String && detail.isNotEmpty) {
          return detail;
        }
      }
    }
    return error.toString();
  }
}
