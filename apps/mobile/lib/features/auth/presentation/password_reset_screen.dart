import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../application/auth_api.dart';

class PasswordResetScreen extends ConsumerStatefulWidget {
  const PasswordResetScreen({super.key});

  @override
  ConsumerState<PasswordResetScreen> createState() =>
      _PasswordResetScreenState();
}

class _PasswordResetScreenState extends ConsumerState<PasswordResetScreen> {
  final _requestKey = GlobalKey<FormState>();
  final _confirmKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _token = TextEditingController();
  final _password = TextEditingController();
  final _confirmation = TextEditingController();
  bool _requested = false;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _token.dispose();
    _password.dispose();
    _confirmation.dispose();
    super.dispose();
  }

  Future<void> _request() async {
    if (!(_requestKey.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(authApiProvider)
          .requestPasswordReset(email: _email.text.trim());
      if (mounted) setState(() => _requested = true);
    } on DioException catch (error) {
      if (mounted) setState(() => _error = _problemDetail(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _confirm() async {
    if (!(_confirmKey.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(authApiProvider)
          .confirmPasswordReset(
            token: _token.text.trim(),
            newPassword: _password.text,
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(AppLocalizations.of(context).passwordResetSuccess),
          ),
        );
        context.go('/login');
      }
    } on DioException catch (error) {
      if (mounted) setState(() => _error = _problemDetail(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _problemDetail(DioException error) {
    final data = error.response?.data;
    if (data is Map<String, dynamic> && data['detail'] is String) {
      return data['detail'] as String;
    }
    return AppLocalizations.of(context).passwordResetError;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.passwordResetTitle)),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: _requested ? _confirmationForm(l10n) : _requestForm(l10n),
            ),
          ),
        ),
      ),
    );
  }

  Widget _requestForm(AppLocalizations l10n) {
    return Form(
      key: _requestKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Text(l10n.passwordResetDescription, textAlign: TextAlign.center),
          const SizedBox(height: 24),
          TextFormField(
            controller: _email,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const <String>[AutofillHints.email],
            decoration: InputDecoration(labelText: l10n.emailLabel),
            validator: (value) => value == null || !value.contains('@')
                ? l10n.emailValidation
                : null,
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _busy ? null : _request,
            child: Text(l10n.sendResetInstructions),
          ),
          if (_error != null) ...<Widget>[
            const SizedBox(height: 16),
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
        ],
      ),
    );
  }

  Widget _confirmationForm(AppLocalizations l10n) {
    return Form(
      key: _confirmKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Text(l10n.passwordResetSent, textAlign: TextAlign.center),
          const SizedBox(height: 24),
          TextFormField(
            controller: _token,
            decoration: InputDecoration(
              labelText: l10n.passwordResetTokenLabel,
            ),
            validator: (value) => value == null || value.trim().length < 32
                ? l10n.passwordResetTokenValidation
                : null,
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _password,
            obscureText: true,
            autofillHints: const <String>[AutofillHints.newPassword],
            decoration: InputDecoration(labelText: l10n.newPasswordLabel),
            validator: (value) => value == null || value.length < 8
                ? l10n.passwordValidation
                : null,
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _confirmation,
            obscureText: true,
            decoration: InputDecoration(labelText: l10n.confirmPasswordLabel),
            validator: (value) =>
                value != _password.text ? l10n.passwordsDoNotMatch : null,
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _busy ? null : _confirm,
            child: Text(l10n.savePasswordButton),
          ),
          TextButton(
            onPressed: _busy ? null : () => setState(() => _requested = false),
            child: Text(l10n.resendResetInstructions),
          ),
          if (_error != null) ...<Widget>[
            const SizedBox(height: 16),
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
        ],
      ),
    );
  }
}
