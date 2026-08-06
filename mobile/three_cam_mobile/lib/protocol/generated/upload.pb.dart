// This is a generated file - do not edit.
//
// Generated from upload.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

/// Server -> node: where/how to push a finished recording (failure_recovery.md's
/// upload-chunk-retry table governs the HTTP side; this just tells the node the
/// endpoint + a short-lived token). Sent right after Event.UPLOAD_STARTED would be
/// expected from the node's own perspective, but the ticket itself always originates
/// server-side because the upload endpoint/port is server config, not node config.
class UploadTicket extends $pb.GeneratedMessage {
  factory UploadTicket({
    $core.String? videoName,
    $core.String? uploadUrl,
    $core.String? uploadToken,
  }) {
    final result = create();
    if (videoName != null) result.videoName = videoName;
    if (uploadUrl != null) result.uploadUrl = uploadUrl;
    if (uploadToken != null) result.uploadToken = uploadToken;
    return result;
  }

  UploadTicket._();

  factory UploadTicket.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory UploadTicket.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'UploadTicket',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'threecam.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'videoName')
    ..aOS(2, _omitFieldNames ? '' : 'uploadUrl')
    ..aOS(3, _omitFieldNames ? '' : 'uploadToken')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UploadTicket clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UploadTicket copyWith(void Function(UploadTicket) updates) =>
      super.copyWith((message) => updates(message as UploadTicket))
          as UploadTicket;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UploadTicket create() => UploadTicket._();
  @$core.override
  UploadTicket createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static UploadTicket getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<UploadTicket>(create);
  static UploadTicket? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get videoName => $_getSZ(0);
  @$pb.TagNumber(1)
  set videoName($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasVideoName() => $_has(0);
  @$pb.TagNumber(1)
  void clearVideoName() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get uploadUrl => $_getSZ(1);
  @$pb.TagNumber(2)
  set uploadUrl($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasUploadUrl() => $_has(1);
  @$pb.TagNumber(2)
  void clearUploadUrl() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get uploadToken => $_getSZ(2);
  @$pb.TagNumber(3)
  set uploadToken($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasUploadToken() => $_has(2);
  @$pb.TagNumber(3)
  void clearUploadToken() => $_clearField(3);
}

/// Node -> server, informational progress for the Dashboard (independent of the actual
/// HTTP resumable transfer, which is the source of truth for completion).
class UploadProgress extends $pb.GeneratedMessage {
  factory UploadProgress({
    $core.String? videoName,
    $fixnum.Int64? bytesSent,
    $fixnum.Int64? totalBytes,
  }) {
    final result = create();
    if (videoName != null) result.videoName = videoName;
    if (bytesSent != null) result.bytesSent = bytesSent;
    if (totalBytes != null) result.totalBytes = totalBytes;
    return result;
  }

  UploadProgress._();

  factory UploadProgress.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory UploadProgress.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'UploadProgress',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'threecam.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'videoName')
    ..a<$fixnum.Int64>(
        2, _omitFieldNames ? '' : 'bytesSent', $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..a<$fixnum.Int64>(
        3, _omitFieldNames ? '' : 'totalBytes', $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UploadProgress clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UploadProgress copyWith(void Function(UploadProgress) updates) =>
      super.copyWith((message) => updates(message as UploadProgress))
          as UploadProgress;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UploadProgress create() => UploadProgress._();
  @$core.override
  UploadProgress createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static UploadProgress getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<UploadProgress>(create);
  static UploadProgress? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get videoName => $_getSZ(0);
  @$pb.TagNumber(1)
  set videoName($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasVideoName() => $_has(0);
  @$pb.TagNumber(1)
  void clearVideoName() => $_clearField(1);

  @$pb.TagNumber(2)
  $fixnum.Int64 get bytesSent => $_getI64(1);
  @$pb.TagNumber(2)
  set bytesSent($fixnum.Int64 value) => $_setInt64(1, value);
  @$pb.TagNumber(2)
  $core.bool hasBytesSent() => $_has(1);
  @$pb.TagNumber(2)
  void clearBytesSent() => $_clearField(2);

  @$pb.TagNumber(3)
  $fixnum.Int64 get totalBytes => $_getI64(2);
  @$pb.TagNumber(3)
  set totalBytes($fixnum.Int64 value) => $_setInt64(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTotalBytes() => $_has(2);
  @$pb.TagNumber(3)
  void clearTotalBytes() => $_clearField(3);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
