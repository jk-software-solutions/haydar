import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../application/auth_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _identifierController = TextEditingController();
  final _passwordController = TextEditingController();

  String? _errorText;
  bool _showPassword = false;

  @override
  void dispose() {
    _identifierController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    setState(() {
      _errorText = null;
    });
    try {
      await ref
          .read(authControllerProvider.notifier)
          .signIn(
            identifier: _identifierController.text.trim(),
            password: _passwordController.text,
          );
      if (mounted) {
        context.go('/app');
      }
    } on DioException catch (error) {
      if (mounted) {
        setState(() => _errorText = _friendlyError(error));
      }
    } on Object {
      if (mounted) {
        setState(
          () => _errorText = AppLocalizations.of(context).loginConnectionError,
        );
      }
    }
  }

  String _friendlyError(DioException error) {
    final data = error.response?.data;
    if (data is Map<String, dynamic>) {
      final code = data['code'] as String?;
      final l10n = AppLocalizations.of(context);
      final localized = switch (code) {
        'invalid_credentials' => l10n.invalidCredentials,
        'account_inactive' => l10n.permissionDenied,
        _ => null,
      };
      if (localized != null) return localized;
      final detail = data['detail'];
      if (detail is String &&
          detail.isNotEmpty &&
          !detail.contains('Traceback')) {
        return detail;
      }
    }
    return AppLocalizations.of(context).loginConnectionError;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final textTheme = Theme.of(context).textTheme;
    final authState = ref.watch(authControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.loginTitle)),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    Text(
                      'DawamTech | دوام تك',
                      textAlign: TextAlign.center,
                      style: textTheme.titleLarge?.copyWith(
                        color: Theme.of(context).colorScheme.primary,
                        letterSpacing: 1.2,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 20),
                    Text(
                      l10n.loginTitle,
                      textAlign: TextAlign.center,
                      style: textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      l10n.loginSubtitle,
                      textAlign: TextAlign.center,
                      style: textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 24),
                    TextFormField(
                      controller: _identifierController,
                      keyboardType: TextInputType.text,
                      autofillHints: const <String>[AutofillHints.username],
                      decoration: InputDecoration(
                        labelText: l10n.emailLabel,
                        prefixIcon: const Icon(Icons.alternate_email_rounded),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().length < 5) {
                          return l10n.emailValidation;
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _passwordController,
                      obscureText: !_showPassword,
                      autofillHints: const <String>[AutofillHints.password],
                      decoration: InputDecoration(
                        labelText: l10n.passwordLabel,
                        prefixIcon: const Icon(Icons.lock_outline_rounded),
                        suffixIcon: IconButton(
                          tooltip: _showPassword
                              ? (Localizations.localeOf(context).languageCode ==
                                        'ar'
                                    ? 'إخفاء كلمة المرور'
                                    : 'Hide password')
                              : (Localizations.localeOf(context).languageCode ==
                                        'ar'
                                    ? 'إظهار كلمة المرور'
                                    : 'Show password'),
                          onPressed: () =>
                              setState(() => _showPassword = !_showPassword),
                          icon: Icon(
                            _showPassword
                                ? Icons.visibility_off_outlined
                                : Icons.visibility_outlined,
                          ),
                        ),
                      ),
                      validator: (value) {
                        if (value == null || value.length < 8) {
                          return l10n.passwordValidation;
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 20),
                    FilledButton.icon(
                      onPressed: authState.isSubmitting ? null : _submit,
                      icon: authState.isSubmitting
                          ? const SizedBox.square(
                              dimension: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.login_rounded),
                      label: Text(l10n.loginButton),
                    ),
                    const SizedBox(height: 8),
                    TextButton(
                      onPressed: authState.isSubmitting
                          ? null
                          : () => context.push('/forgot-password'),
                      child: Text(l10n.forgotPasswordButton),
                    ),
                    TextButton(
                      onPressed: authState.isSubmitting
                          ? null
                          : () => context.push('/activate-invitation'),
                      child: Text(l10n.haveInvitationButton),
                    ),
                    if (_errorText != null) ...<Widget>[
                      const SizedBox(height: 16),
                      Text(
                        _errorText!,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
