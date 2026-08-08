import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../auth/application/auth_api.dart';

final taskApiProvider = Provider<TaskApi>(
  (ref) => TaskApi(ref.watch(dioProvider)),
);

class TaskApi {
  TaskApi(this.dio);
  final Dio dio;

  Options _auth(AuthSession session) => Options(
    headers: <String, String>{'Authorization': 'Bearer ${session.accessToken}'},
  );

  Future<List<WorkTask>> list(
    AuthSession session, {
    bool allCompany = false,
  }) async {
    final response = await dio.get<List<dynamic>>(
      allCompany ? '/tasks' : '/tasks?mine=true',
      options: _auth(session),
    );
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(WorkTask.fromJson)
        .toList(growable: false);
  }

  Future<void> updateStatus(
    AuthSession session,
    WorkTask task,
    String status,
    String? reason,
  ) async {
    await dio.post<void>(
      '/tasks/${task.id}/status',
      options: _auth(session),
      data: <String, dynamic>{
        'version': task.version,
        'status': status,
        if (reason != null && reason.isNotEmpty) 'reason': reason,
      },
    );
  }

  Future<void> addComment(
    AuthSession session,
    String taskId,
    String body,
  ) async {
    await dio.post<void>(
      '/tasks/$taskId/comments',
      options: _auth(session),
      data: <String, String>{'body': body},
    );
  }

  Future<List<TaskComment>> comments(AuthSession session, String taskId) async {
    final response = await dio.get<List<dynamic>>(
      '/tasks/$taskId/comments',
      options: _auth(session),
    );
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(TaskComment.fromJson)
        .toList(growable: false);
  }
}

class TaskComment {
  const TaskComment({
    required this.id,
    required this.authorMembershipId,
    required this.body,
    required this.createdAt,
  });

  factory TaskComment.fromJson(Map<String, dynamic> json) => TaskComment(
    id: json['id'] as String? ?? '',
    authorMembershipId: json['author_membership_id'] as String? ?? '',
    body: json['body'] as String? ?? '',
    createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
  );

  final String id;
  final String authorMembershipId;
  final String body;
  final DateTime? createdAt;
}

class WorkTask {
  const WorkTask({
    required this.id,
    required this.title,
    required this.description,
    required this.priority,
    required this.status,
    required this.dueAt,
    required this.version,
  });
  factory WorkTask.fromJson(Map<String, dynamic> json) => WorkTask(
    id: json['id'] as String? ?? '',
    title: json['title'] as String? ?? '',
    description: json['description'] as String? ?? '',
    priority: json['priority'] as String? ?? 'normal',
    status: json['status'] as String? ?? 'new',
    dueAt: DateTime.tryParse(json['due_at'] as String? ?? ''),
    version: json['version'] as int? ?? 1,
  );
  final String id;
  final String title;
  final String description;
  final String priority;
  final String status;
  final DateTime? dueAt;
  final int version;
}
