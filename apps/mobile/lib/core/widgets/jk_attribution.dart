import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

class JkAttribution extends StatelessWidget {
  const JkAttribution({this.compact = false, super.key});

  final bool compact;

  static final Uri _website = Uri.https('jksoftwaresolutions.com');
  static final Uri _whatsApp = Uri.https('wa.me', '/96170309152');

  @override
  Widget build(BuildContext context) {
    final ar = Localizations.localeOf(context).languageCode == 'ar';
    final small = Theme.of(context).textTheme.labelSmall;
    return Wrap(
      alignment: WrapAlignment.center,
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: compact ? 6 : 12,
      runSpacing: 4,
      children: <Widget>[
        Semantics(
          link: true,
          child: InkWell(
            onTap: () => launchUrl(_website, mode: LaunchMode.externalApplication),
            child: Wrap(
              alignment: WrapAlignment.center,
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 5,
              children: <Widget>[
                Image.asset(
                  'assets/branding/jk_main_logo.png',
                  height: compact ? 18 : 32,
                  semanticLabel: 'JK Software Solutions',
                ),
                Text(
                  ar ? 'تطوير JK Software Solutions' : 'Developed by JK Software Solutions',
                  style: small?.copyWith(fontSize: compact ? 9 : null),
                ),
              ],
            ),
          ),
        ),
        Semantics(
          link: true,
          child: InkWell(
            onTap: () => launchUrl(_whatsApp, mode: LaunchMode.externalApplication),
            child: Text(
              '+961 70 309 152',
              textDirection: TextDirection.ltr,
              style: small?.copyWith(
                fontSize: compact ? 9 : null,
                decoration: TextDecoration.underline,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
