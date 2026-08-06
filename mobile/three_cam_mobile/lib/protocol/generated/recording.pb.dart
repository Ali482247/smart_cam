// This is a generated file - do not edit.
//
// Generated from recording.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;

import 'recording.pbenum.dart';

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

export 'recording.pbenum.dart';

/// Node -> server, informational recording state (protocol_specification.md §Envelope).
class StatusUpdate extends $pb.GeneratedMessage {
  factory StatusUpdate({
    $core.bool? recording,
    $core.double? actualFps,
    $core.String? activeVideoName,
    $fixnum.Int64? recordingStartedAtMs,
  }) {
    final result = create();
    if (recording != null) result.recording = recording;
    if (actualFps != null) result.actualFps = actualFps;
    if (activeVideoName != null) result.activeVideoName = activeVideoName;
    if (recordingStartedAtMs != null)
      result.recordingStartedAtMs = recordingStartedAtMs;
    return result;
  }

  StatusUpdate._();

  factory StatusUpdate.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory StatusUpdate.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'StatusUpdate',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'threecam.v1'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'recording')
    ..aD(2, _omitFieldNames ? '' : 'actualFps', fieldType: $pb.PbFieldType.OF)
    ..aOS(3, _omitFieldNames ? '' : 'activeVideoName')
    ..aInt64(4, _omitFieldNames ? '' : 'recordingStartedAtMs')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  StatusUpdate clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  StatusUpdate copyWith(void Function(StatusUpdate) updates) =>
      super.copyWith((message) => updates(message as StatusUpdate))
          as StatusUpdate;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static StatusUpdate create() => StatusUpdate._();
  @$core.override
  StatusUpdate createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static StatusUpdate getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<StatusUpdate>(create);
  static StatusUpdate? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get recording => $_getBF(0);
  @$pb.TagNumber(1)
  set recording($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasRecording() => $_has(0);
  @$pb.TagNumber(1)
  void clearRecording() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.double get actualFps => $_getN(1);
  @$pb.TagNumber(2)
  set actualFps($core.double value) => $_setFloat(1, value);
  @$pb.TagNumber(2)
  $core.bool hasActualFps() => $_has(1);
  @$pb.TagNumber(2)
  void clearActualFps() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get activeVideoName => $_getSZ(2);
  @$pb.TagNumber(3)
  set activeVideoName($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasActiveVideoName() => $_has(2);
  @$pb.TagNumber(3)
  void clearActiveVideoName() => $_clearField(3);

  @$pb.TagNumber(4)
  $fixnum.Int64 get recordingStartedAtMs => $_getI64(3);
  @$pb.TagNumber(4)
  set recordingStartedAtMs($fixnum.Int64 value) => $_setInt64(3, value);
  @$pb.TagNumber(4)
  $core.bool hasRecordingStartedAtMs() => $_has(3);
  @$pb.TagNumber(4)
  void clearRecordingStartedAtMs() => $_clearField(4);
}

/// Internal event catalogue (network_architecture.md §Event Layer).
class Event extends $pb.GeneratedMessage {
  factory Event({
    Event_Type? type,
    $core.String? detail,
  }) {
    final result = create();
    if (type != null) result.type = type;
    if (detail != null) result.detail = detail;
    return result;
  }

  Event._();

  factory Event.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Event.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Event',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'threecam.v1'),
      createEmptyInstance: create)
    ..aE<Event_Type>(1, _omitFieldNames ? '' : 'type',
        enumValues: Event_Type.values)
    ..aOS(2, _omitFieldNames ? '' : 'detail')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Event clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Event copyWith(void Function(Event) updates) =>
      super.copyWith((message) => updates(message as Event)) as Event;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Event create() => Event._();
  @$core.override
  Event createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static Event getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Event>(create);
  static Event? _defaultInstance;

  @$pb.TagNumber(1)
  Event_Type get type => $_getN(0);
  @$pb.TagNumber(1)
  set type(Event_Type value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasType() => $_has(0);
  @$pb.TagNumber(1)
  void clearType() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get detail => $_getSZ(1);
  @$pb.TagNumber(2)
  set detail($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasDetail() => $_has(1);
  @$pb.TagNumber(2)
  void clearDetail() => $_clearField(2);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
