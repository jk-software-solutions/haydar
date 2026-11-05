import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../../../core/network/api_client.dart';
import '../../auth/application/auth_api.dart';

class AdminWebPortalScreen extends StatefulWidget {
  const AdminWebPortalScreen({required this.session, super.key});

  final AuthSession session;

  @override
  State<AdminWebPortalScreen> createState() => _AdminWebPortalScreenState();
}

class _AdminWebPortalScreenState extends State<AdminWebPortalScreen> {
  WebViewController? _controller;
  var _progress = 0;
  var _showHint = true;
  String? _loadError;

  bool get _ar => Localizations.localeOf(context).languageCode == 'ar';

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_controller != null) return;
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (progress) => setState(() => _progress = progress),
          onPageFinished: (_) => setState(() {
            _progress = 100;
            _loadError = null;
          }),
          onWebResourceError: (error) {
            // Never leave the raw API JSON on screen. Give the administrator
            // a clear recovery action instead.
            if (error.isForMainFrame ?? true) {
              setState(
                () => _loadError = _ar
                    ? 'تعذر فتح بوابة الإدارة. اضغط إعادة المحاولة أو افتح الموقع من المتصفح.'
                    : 'The administration portal could not be opened. Retry or open it in a browser.',
              );
            }
          },
        ),
      )
      ..loadRequest(
        _companyPortalUri(Localizations.localeOf(context).languageCode),
        headers: <String, String>{
          'Authorization': 'Bearer ${widget.session.accessToken}',
          'X-Refresh-Token': widget.session.refreshToken,
        },
      );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(_ar ? 'كل تحكمات الموقع' : 'All site controls'),
      actions: <Widget>[
        IconButton(
          tooltip: _ar ? 'تحديث' : 'Reload',
          onPressed: () => _controller?.reload(),
          icon: const Icon(Icons.refresh_rounded),
        ),
      ],
      bottom: _progress < 100
          ? PreferredSize(
              preferredSize: const Size.fromHeight(3),
              child: LinearProgressIndicator(value: _progress / 100),
            )
          : null,
    ),
    body: _loadError != null
        ? Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  const Icon(Icons.cloud_off_rounded, size: 52),
                  const SizedBox(height: 12),
                  Text(_loadError!, textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed: () {
                      setState(() {
                        _loadError = null;
                        _progress = 0;
                      });
                      _controller?.loadRequest(
                        _companyPortalUri(
                          Localizations.localeOf(context).languageCode,
                        ),
                        headers: <String, String>{
                          'Authorization':
                              'Bearer ${widget.session.accessToken}',
                          'X-Refresh-Token': widget.session.refreshToken,
                        },
                      );
                    },
                    icon: const Icon(Icons.refresh_rounded),
                    label: Text(_ar ? 'إعادة المحاولة' : 'Retry'),
                  ),
                ],
              ),
            ),
          )
        : _controller == null
        ? const Center(child: CircularProgressIndicator())
        : Stack(
            children: <Widget>[
              WebViewWidget(controller: _controller!),
              if (_showHint)
                PositionedDirectional(
                  start: 12,
                  end: 12,
                  bottom: 12,
                  child: SafeArea(
                    child: Card(
                      elevation: 8,
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Row(
                          children: <Widget>[
                            const Icon(Icons.touch_app_rounded),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _ar
                                    ? 'هذه بوابة الموقع كاملة داخل التطبيق. استخدم التبويبات بالأعلى، ويمكنك التكبير إذا احتجت.'
                                    : 'This is the full web admin portal inside the app. Use the top tabs; pinch zoom if needed.',
                              ),
                            ),
                            IconButton(
                              tooltip: _ar ? 'إخفاء' : 'Dismiss',
                              onPressed: () =>
                                  setState(() => _showHint = false),
                              icon: const Icon(Icons.close_rounded),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
  );
}

Uri _companyPortalUri(String languageCode) {
  final apiUri = Uri.parse(apiBaseUrl);
  final locale = languageCode == 'ar' ? 'ar' : 'en';
  return Uri(
    scheme: apiUri.scheme,
    host: apiUri.host,
    port: apiUri.hasPort ? apiUri.port : null,
    path: '/$locale/mobile-session',
    queryParameters: <String, String>{'lang': locale},
  );
}
