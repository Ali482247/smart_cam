// This is a generated file - do not edit.
//
// Generated from scheduler.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;

import 'common.pbenum.dart' as $0;
import 'scheduler.pbenum.dart';

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

export 'scheduler.pbenum.dart';

/// NTP-style 4-timestamp clock sync exchange (clock_synchronization.md §Exchange algorithm).
class ClockSyncRequest extends $pb.GeneratedMessage {
  factory ClockSyncRequest({
    $fixnum.Int64? t0Ms,
  }) {
    final result = create();
    if (t0Ms != null) result.t0Ms = t0Ms;
    return result;
  }

  ClockSyncRequest._();

  factory ClockSyncRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ClockSyncRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ClockSyncRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'threecam.v1'),
      createEmptyInstance: create)
    ..aInt64(1, _omitFieldNames ? '' : 't0Ms')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ClockSyncRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ClockSyncRequest copyWith(void Function(ClockSyncRequest) updates) =>
      super.copyWith((message) => updates(message as ClockSyncRequest))
          as ClockSyncRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ClockSyncRequest create() => ClockSyncRequest._();
  @$core.override
  ClockSyncRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ClockSyncRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ClockSyncRequest>(create);
  static ClockSyncRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $fixnum.Int64 get t0Ms => $_getI64(0);
  @$pb.TagNumber(1)
  set t0Ms($fixnum.Int64 value) => $_setInt64(0, value);
  @$pb.TagNumber(1)
  $core.bool hasT0Ms() => $_has(0);
  @$pb.TagNumber(1)
  void clearT0Ms() => $_clearField(1);
}

class ClockSyncReply extends $pb.GeneratedMessage {
  factory ClockSyncReply({
    $fixnum.Int64? t0Ms,
    $fixnum.Int64? t1Ms,
    $fixnum.Int64? t2Ms,
  }) {
    final result = create();
    if (t0Ms != null) result.t0Ms = t0Ms;
    if (t1Ms != null) result.t1Ms = t1Ms;
    if (t2Ms != null) result.t2Ms = t2Ms;
    return result;
  }

  ClockSyncReply._();

  factory ClockSyncReply.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ClockSyncReply.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ClockSyncReply',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'threecam.v1'),
      createEmptyInstance: create)
    ..aInt64(1, _omitFieldNames ? '' : 't0Ms')
    ..aInt64(2, _omitFieldNames ? '' : 't1Ms')
    ..aInt64(3, _omitFieldNames ? '' : 't2Ms')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ClockSyncReply clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ClockSyncReply copyWith(void Function(ClockSyncReply) updates) =>
      super.copyWith((message) => updates(message as ClockSyncReply))
          as ClockSyncReply;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ClockSyncReply create() => ClockSyncReply._();
  @$core.override
  ClockSyncReply createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ClockSyncReply getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ClockSyncReply>(create);
  static ClockSyncReply? _defaultInstance;

  @$pb.TagNumber(1)
  $fixnum.Int64 get t0Ms => $_getI64(0);
  @$pb.TagNumber(1)
  set t0Ms($fixnum.Int64 value) => $_setInt64(0, value);
  @$pb.TagNumber(1)
  $core.bool hasT0Ms() => $_has(0);
  @$pb.TagNumber(1)
  void clearT0Ms() => $_clearField(1);

  @$pb.TagNumber(2)
  $fixnum.Int64 get t1Ms => $_getI64(1);
  @$pb.TagNumber(2)
  set t1Ms($fixnum.Int64 value) => $_setInt64(1, value);
  @$pb.TagNumber(2)
  $core.bool hasT1Ms() => $_has(1);
  @$pb.TagNumber(2)
  void clearT1Ms() => $_clearField(2);

  @$pb.TagNumber(3)
  $fixnum.Int64 get t2Ms => $_getI64(2);
  @$pb.TagNumber(3)
  set t2Ms($fixnum.Int64 value) => $_setInt64(2, value);
  @$pb.TagNumber(3)
  $core.bool hasT2Ms() => $_has(2);
  @$pb.TagNumber(3)
  void clearT2Ms() => $_clearField(3);
}

/// Server -> node, broadcast by the Scheduler (scheduler.md §Algorithm).
class ScheduledCommand extends $pb.GeneratedMessage {
  factory ScheduledCommand({
    ScheduledCommand_Type? type,
    $fixnum.Int64? executeAtMs,
    $core.String? commandId,
    $core.String? cameraName,
    $core.String? sessionLabel,
    $core.int? recordIndex,
  }) {
    final result = create();
    if (type != null) result.type = type;
    if (executeAtMs != null) result.executeAtMs = executeAtMs;
    if (commandId != null) result.commandId = commandId;
    if (cameraName != null) result.cameraName = cameraName;
    if (sessionLabel != null) result.sessionLabel = sessionLabel;
    if (recordIndex != null) result.recordIndex = recordIndex;
    return result;
  }

  ScheduledCommand._();

  factory ScheduledCommand.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ScheduledCommand.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ScheduledCommand',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'threecam.v1'),
      createEmptyInstance: create)
    ..aE<ScheduledCommand_Type>(1, _omitFieldNames ? '' : 'type',
        enumValues: ScheduledCommand_Type.values)
    ..aInt64(2, _omitFieldNames ? '' : 'executeAtMs')
    ..aOS(3, _omitFieldNames ? '' : 'commandId')
    ..aOS(4, _omitFieldNames ? '' : 'cameraName')
    ..aOS(5, _omitFieldNames ? '' : 'sessionLabel')
    ..aI(6, _omitFieldNames ? '' : 'recordIndex',
        fieldType: $pb.PbFieldType.OU3)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScheduledCommand clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScheduledCommand copyWith(void Function(ScheduledCommand) updates) =>
      super.copyWith((message) => updates(message as ScheduledCommand))
          as ScheduledCommand;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ScheduledCommand create() => ScheduledCommand._();
  @$core.override
  ScheduledCommand createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ScheduledCommand getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ScheduledCommand>(create);
  static ScheduledCommand? _defaultInstance;

  @$pb.TagNumber(1)
  ScheduledCommand_Type get type => $_getN(0);
  @$pb.TagNumber(1)
  set type(ScheduledCommand_Type value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasType() => $_has(0);
  @$pb.TagNumber(1)
  void clearType() => $_clearField(1);

  @$pb.TagNumber(2)
  $fixnum.Int64 get executeAtMs => $_getI64(1);
  @$pb.TagNumber(2)
  set executeAtMs($fixnum.Int64 value) => $_setInt64(1, value);
  @$pb.TagNumber(2)
  $core.bool hasExecuteAtMs() => $_has(1);
  @$pb.TagNumber(2)
  void clearExecuteAtMs() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get commandId => $_getSZ(2);
  @$pb.TagNumber(3)
  set commandId($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasCommandId() => $_has(2);
  @$pb.TagNumber(3)
  void clearCommandId() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get cameraName => $_getSZ(3);
  @$pb.TagNumber(4)
  set cameraName($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasCameraName() => $_has(3);
  @$pb.TagNumber(4)
  void clearCameraName() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get sessionLabel => $_getSZ(4);
  @$pb.TagNumber(5)
  set sessionLabel($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasSessionLabel() => $_has(4);
  @$pb.TagNumber(5)
  void clearSessionLabel() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.int get recordIndex => $_getIZ(5);
  @$pb.TagNumber(6)
  set recordIndex($core.int value) => $_setUnsignedInt32(5, value);
  @$pb.TagNumber(6)
  $core.bool hasRecordIndex() => $_has(5);
  @$pb.TagNumber(6)
  void clearRecordIndex() => $_clearField(6);
}

/// Node -> server, correlates to command_id (protocol_specification.md §ACK/Retry/...).
class Ack extends $pb.GeneratedMessage {
  factory Ack({
    $core.String? commandId,
    $0.ResultCode? result,
  }) {
    final result$ = create();
    if (commandId != null) result$.commandId = commandId;
    if (result != null) result$.result = result;
    return result$;
  }

  Ack._();

  factory Ack.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Ack.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Ack',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'threecam.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'commandId')
    ..aE<$0.ResultCode>(2, _omitFieldNames ? '' : 'result',
        enumValues: $0.ResultCode.values)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Ack clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Ack copyWith(void Function(Ack) updates) =>
      super.copyWith((message) => updates(message as Ack)) as Ack;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Ack create() => Ack._();
  @$core.override
  Ack createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static Ack getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Ack>(create);
  static Ack? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get commandId => $_getSZ(0);
  @$pb.TagNumber(1)
  set commandId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasCommandId() => $_has(0);
  @$pb.TagNumber(1)
  void clearCommandId() => $_clearField(1);

  @$pb.TagNumber(2)
  $0.ResultCode get result => $_getN(1);
  @$pb.TagNumber(2)
  set result($0.ResultCode value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasResult() => $_has(1);
  @$pb.TagNumber(2)
  void clearResult() => $_clearField(2);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
