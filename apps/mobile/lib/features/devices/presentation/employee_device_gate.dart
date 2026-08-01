import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../application/device_api.dart';

class EmployeeDeviceGate extends ConsumerWidget {
  const EmployeeDeviceGate({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final binding = ref.watch(deviceBindingProvider);
    return binding.when(
      loading: () =>
          const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (_, _) =>
          _DeviceError(onRetry: () => ref.invalidate(deviceBindingProvider)),
      data: (value) {
        if (value.isApproved) return child;
        if (value.needsChangeReason) return const _ReplacementReasonScreen();
        return const _PendingApprovalScreen();
      },
    );
  }
}

class _ReplacementReasonScreen extends ConsumerStatefulWidget {
  const _ReplacementReasonScreen();

  @override
  ConsumerState<_ReplacementReasonScreen> createState() =>
      _ReplacementReasonScreenState();
}

class _ReplacementReasonScreenState
    extends ConsumerState<_ReplacementReasonScreen> {
  final _controller = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_controller.text.trim().length < 5) {
      setState(
        () => _error = AppLocalizations.of(context).deviceReasonValidation,
      );
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await ref
          .read(deviceApiProvider)
          .ensureCurrentInstallation(reason: _controller.text.trim());
      ref.invalidate(deviceBindingProvider);
    } on Object {
      if (mounted) {
        setState(() {
          _submitting = false;
          _error = AppLocalizations.of(context).deviceRegistrationError;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.deviceApprovalTitle)),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                const Icon(Icons.phonelink_lock_outlined, size: 64),
                const SizedBox(height: 16),
                Text(
                  l10n.deviceReplacementDescription,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 20),
                TextField(
                  controller: _controller,
                  minLines: 3,
                  maxLines: 5,
                  decoration: InputDecoration(
                    labelText: l10n.deviceChangeReasonLabel,
                    errorText: _error,
                  ),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _submitting ? null : _submit,
                  child: Text(l10n.requestDeviceChangeButton),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _PendingApprovalScreen extends StatelessWidget {
  const _PendingApprovalScreen();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.deviceApprovalTitle)),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const Icon(Icons.hourglass_top_rounded, size: 64),
              const SizedBox(height: 16),
              Text(l10n.devicePendingApproval, textAlign: TextAlign.center),
            ],
          ),
        ),
      ),
    );
  }
}

class _DeviceError extends StatelessWidget {
  const _DeviceError({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Text(l10n.deviceRegistrationError),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onRetry, child: Text(l10n.retryButton)),
          ],
        ),
      ),
    );
  }
}
