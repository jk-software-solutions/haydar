import 'package:dio/dio.dart';

/// Returns a content type understood by the API for common employee uploads.
/// Dio normally infers this from the extension; keeping the mapping here also
/// covers files selected from Android providers that omit a MIME type.
DioMediaType uploadMediaType(String filename) {
  final extension = filename.split('.').last.toLowerCase();
  final value = switch (extension) {
    'pdf' => DioMediaType('application', 'pdf'),
    'jpg' || 'jpeg' => DioMediaType('image', 'jpeg'),
    'png' => DioMediaType('image', 'png'),
    'webp' => DioMediaType('image', 'webp'),
    'txt' => DioMediaType('text', 'plain'),
    'docx' => DioMediaType(
      'application',
      'vnd.openxmlformats-officedocument.wordprocessingml.document',
    ),
    'xlsx' => DioMediaType(
      'application',
      'vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ),
    'aac' => DioMediaType('audio', 'aac'),
    'm4a' || 'mp4' => DioMediaType('audio', 'mp4'),
    'mp3' => DioMediaType('audio', 'mpeg'),
    'ogg' => DioMediaType('audio', 'ogg'),
    'wav' => DioMediaType('audio', 'wav'),
    'webm' => DioMediaType('audio', 'webm'),
    '3gp' || '3gpp' => DioMediaType('audio', '3gpp'),
    _ => DioMediaType('application', 'octet-stream'),
  };
  return value;
}
