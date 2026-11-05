import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/file_upload.dart';
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

  Future<List<TaskRecipient>> recipients(AuthSession session) async {
    final response = await dio.get<List<dynamic>>(
      '/tasks/recipients',
      options: _auth(session),
    );
    return (response.data ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(TaskRecipient.fromJson)
        .toList(growable: false);
  }

  Future<void> create(
    AuthSession session, {
    required String title,
    required String description,
    required String priority,
    required String recipientId,
    DateTime? dueAt,
  }) async {
    await dio.post<void>(
      '/tasks',
      options: _auth(session),
      data: <String, dynamic>{
        'title': title,
        'description': description,
        'priority': priority,
        'membership_ids': <String>[recipientId],
        if (dueAt != null) 'due_at': dueAt.toUtc().toIso8601String(),
      },
    );
  }

  Future<void> updateStatus(
    AuthSession session,
    WorkTask task,
    String status,
    String? reason,
    DateTime? requestedDueAt,
    String? completionAttachmentFileId,
  ) async {
    final data = <String, dynamic>{
      'version': task.version,
      'status': status,
      if (reason != null && reason.isNotEmpty) 'reason': reason,
      if (requestedDueAt != null)
        'requested_due_at': requestedDueAt.toUtc().toIso8601String(),
    };
    if (completionAttachmentFileId != null) {
      data['completion_attachment_file_id'] = completionAttachmentFileId;
    }
    await dio.post<void>(
      '/tasks/${task.id}/status',
      options: _auth(session),
      data: data,
    );
  }

  Future<String> upload(
    AuthSession session, {
    required String filename,
    required List<int> bytes,
  }) async {
    final form = FormData.fromMap(<String, dynamic>{
      'upload': MultipartFile.fromBytes(
        bytes,
        filename: filename,
        contentType: uploadMediaType(filename),
      ),
    });
    final response = await dio.post<Map<String, dynamic>>(
      '/files',
      options: _auth(session),
      data: form,
    );
    return response.data?['id'] as String? ?? '';
  }

  Future<void> decideExtension(
    AuthSession session,
    WorkTask task, {
    required String decision,
    required String comment,
    DateTime? newDueAt,
  }) async {
    await dio.post<void>(
      '/tasks/${task.id}/extension-decision',
      options: _auth(session),
      data: <String, dynamic>{
        'version': task.version,
        'decision': decision,
        'comment': comment,
        if (newDueAt != null) 'new_due_at': newDueAt.toUtc().toIso8601String(),
      },
    );
  }

  Future<void> addComment(
    AuthSession session,
    String taskId,
    String body, {
    String? attachmentFileId,
  }) async {
    await dio.post<void>(
      '/tasks/$taskId/comments',
      options: _auth(session),
      data: <String, dynamic>{
        'body': body,
        ...?attachmentFileId == null
            ? null
            : <String, dynamic>{'attachment_file_id': attachmentFileId},
      },
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
    required this.attachmentFileId,
    required this.createdAt,
  });

  factory TaskComment.fromJson(Map<String, dynamic> json) => TaskComment(
    id: json['id'] as String? ?? '',
    authorMembershipId: json['author_membership_id'] as String? ?? '',
    body: json['body'] as String? ?? '',
    attachmentFileId: json['attachment_file_id'] as String?,
    createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
  );

  final String id;
  final String authorMembershipId;
  final String body;
  final String? attachmentFileId;
  final DateTime? createdAt;
}

class WorkTask {
  const WorkTask({
    required this.id,
    required this.title,
    required this.description,
    required this.createdByMembershipId,
    required this.assigneeIds,
    required this.viewedByIds,
    required this.completionAttachmentFileId,
    required this.priority,
    required this.status,
    required this.dueAt,
    required this.version,
    required this.latestExtension,
  });
  factory WorkTask.fromJson(Map<String, dynamic> json) => WorkTask(
    id: json['id'] as String? ?? '',
    title: json['title'] as String? ?? '',
    description: json['description'] as String? ?? '',
    createdByMembershipId: json['created_by_membership_id'] as String? ?? '',
    assigneeIds: (json['assignee_ids'] as List<dynamic>? ?? <dynamic>[])
        .whereType<String>()
        .toList(growable: false),
    viewedByIds: (json['viewed_by_ids'] as List<dynamic>? ?? <dynamic>[])
        .whereType<String>()
        .toList(growable: false),
    priority: json['priority'] as String? ?? 'normal',
    status: json['status'] as String? ?? 'new',
    dueAt: DateTime.tryParse(json['due_at'] as String? ?? ''),
    version: json['version'] as int? ?? 1,
    completionAttachmentFileId:
        json['completion_attachment_file_id'] as String?,
    latestExtension: json['latest_extension'] is Map<String, dynamic>
        ? TaskExtension.fromJson(
            json['latest_extension'] as Map<String, dynamic>,
          )
        : null,
  );
  final String id;
  final String title;
  final String description;
  final String createdByMembershipId;
  final List<String> assigneeIds;
  final List<String> viewedByIds;
  final String? completionAttachmentFileId;
  final String priority;
  final String status;
  final DateTime? dueAt;
  final int version;
  final TaskExtension? latestExtension;
}

class TaskRecipient {
  const TaskRecipient({
    required this.id,
    required this.displayName,
    required this.email,
    required this.roleCode,
  });

  factory TaskRecipient.fromJson(Map<String, dynamic> json) => TaskRecipient(
    id: json['id'] as String? ?? '',
    displayName: json['display_name'] as String? ?? '',
    email: json['email'] as String? ?? '',
    roleCode: json['role_code'] as String? ?? '',
  );

  final String id;
  final String displayName;
  final String email;
  final String roleCode;
}

class TaskExtension {
  const TaskExtension({
    required this.reason,
    required this.requestedDueAt,
    required this.status,
    required this.decisionComment,
  });

  factory TaskExtension.fromJson(Map<String, dynamic> json) => TaskExtension(
    reason: json['reason'] as String? ?? '',
    requestedDueAt: DateTime.tryParse(
      json['requested_due_at'] as String? ?? '',
    ),
    status: json['status'] as String? ?? '',
    decisionComment: json['decision_comment'] as String?,
  );

  final String reason;
  final DateTime? requestedDueAt;
  final String status;
  final String? decisionComment;
}
