import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../auth/application/auth_controller.dart';

class ActivateInvitationScreen extends ConsumerStatefulWidget {
  const ActivateInvitationScreen({super.key});

  @override
  ConsumerState<ActivateInvitationScreen> createState() =>
      _ActivateInvitationScreenState();
}

class _ActivateInvitationScreenState
    extends ConsumerState<ActivateInvitationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _tokenController = TextEditingController();
  final _passwordController = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _tokenController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _activate() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() => _error = null);
    try {
      await ref
          .read(authControllerProvider.notifier)
          .activateInvitation(
            activationToken: _tokenController.text.trim(),
            password: _passwordController.text,
          );
      if (mounted) context.go('/app');
    } on DioException catch (error) {
      final data = error.response?.data;
      setState(() {
        _error = data is Map<String, dynamic> && data['detail'] is String
            ? data['detail'] as String
            : AppLocalizations.of(context).invitationActivationError;
      });
    } on Object {
      setState(
        () => _error = AppLocalizations.of(context).invitationActivationError,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final submitting = ref.watch(authControllerProvider).isSubmitting;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.activateInvitationTitle)),
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
                    Text(l10n.activateInvitationDescription),
                    const SizedBox(height: 24),
                    TextFormField(
                      controller: _tokenController,
                      minLines: 2,
                      maxLines: 4,
                      decoration: InputDecoration(
                        labelText: l10n.activationTokenLabel,
                      ),
                      validator: (value) =>
                          value == null || value.trim().length < 32
                          ? l10n.activationTokenValidation
                          : null,
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _passwordController,
                      obscureText: true,
                      decoration: InputDecoration(
                        labelText: l10n.newPasswordLabel,
                      ),
                      validator: (value) => value == null || value.length < 8
                          ? l10n.passwordValidation
                          : null,
                    ),
                    const SizedBox(height: 20),
                    FilledButton.icon(
                      onPressed: submitting ? null : _activate,
                      icon: submitting
                          ? const SizedBox.square(
                              dimension: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.verified_user_outlined),
                      label: Text(l10n.activateInvitationButton),
                    ),
                    if (_error != null) ...<Widget>[
                      const SizedBox(height: 16),
                      Text(
                        _error!,
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
