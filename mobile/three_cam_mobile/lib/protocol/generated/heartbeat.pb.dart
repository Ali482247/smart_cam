// This is a generated file - do not edit.
//
// Generated from heartbeat.proto.

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

/// Sent by the node every 5 seconds (connection_lifecycle.md §Heartbeat/keepalive).
class Heartbeat extends $pb.GeneratedMessage {
  factory Heartbeat({
    $core.double? batteryPct,
    $fixnum.Int64? freeStorageBytes,
    $fixnum.Int64? totalStorageBytes,
    $core.double? temperatureC,
    $core.bool? recording,
    $fixnum.Int64? clockOffsetMs,
    $core.int? clockUncertaintyMs,
    $core.double? lastRttMs,
  }) {
    final result = create();
    if (batteryPct != null) result.batteryPct = batteryPct;
    if (freeStorageBytes != null) result.freeStorageBytes = freeStorageBytes;
    if (totalStorageBytes != null) result.totalStorageBytes = totalStorageBytes;
    if (temperatureC != null) result.temperatureC = temperatureC;
    if (recording != null) result.recording = recording;
    if (clockOffsetMs != null) result.clockOffsetMs = clockOffsetMs;
    if (clockUncertaintyMs != null)
      result.clockUncertaintyMs = clockUncertaintyMs;
    if (lastRttMs != null) result.lastRttMs = lastRttMs;
    return result;
  }

  Heartbeat._();

  factory Heartbeat.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Heartbeat.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Heartbeat',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'threecam.v1'),
      createEmptyInstance: create)
    ..aD(1, _omitFieldNames ? '' : 'batteryPct', fieldType: $pb.PbFieldType.OF)
    ..a<$fixnum.Int64>(
        2, _omitFieldNames ? '' : 'freeStorageBytes', $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..a<$fixnum.Int64>(
        3, _omitFieldNames ? '' : 'totalStorageBytes', $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..aD(4, _omitFieldNames ? '' : 'temperatureC',
        fieldType: $pb.PbFieldType.OF)
    ..aOB(5, _omitFieldNames ? '' : 'recording')
    ..aInt64(6, _omitFieldNames ? '' : 'clockOffsetMs')
    ..aI(7, _omitFieldNames ? '' : 'clockUncertaintyMs',
        fieldType: $pb.PbFieldType.OU3)
    ..aD(8, _omitFieldNames ? '' : 'lastRttMs', fieldType: $pb.PbFieldType.OF)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Heartbeat clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Heartbeat copyWith(void Function(Heartbeat) updates) =>
      super.copyWith((message) => updates(message as Heartbeat)) as Heartbeat;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Heartbeat create() => Heartbeat._();
  @$core.override
  Heartbeat createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static Heartbeat getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Heartbeat>(create);
  static Heartbeat? _defaultInstance;

  @$pb.TagNumber(1)
  $core.double get batteryPct => $_getN(0);
  @$pb.TagNumber(1)
  set batteryPct($core.double value) => $_setFloat(0, value);
  @$pb.TagNumber(1)
  $core.bool hasBatteryPct() => $_has(0);
  @$pb.TagNumber(1)
  void clearBatteryPct() => $_clearField(1);

  @$pb.TagNumber(2)
  $fixnum.Int64 get freeStorageBytes => $_getI64(1);
  @$pb.TagNumber(2)
  set freeStorageBytes($fixnum.Int64 value) => $_setInt64(1, value);
  @$pb.TagNumber(2)
  $core.bool hasFreeStorageBytes() => $_has(1);
  @$pb.TagNumber(2)
  void clearFreeStorageBytes() => $_clearField(2);

  @$pb.TagNumber(3)
  $fixnum.Int64 get totalStorageBytes => $_getI64(2);
  @$pb.TagNumber(3)
  set totalStorageBytes($fixnum.Int64 value) => $_setInt64(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTotalStorageBytes() => $_has(2);
  @$pb.TagNumber(3)
  void clearTotalStorageBytes() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.double get temperatureC => $_getN(3);
  @$pb.TagNumber(4)
  set temperatureC($core.double value) => $_setFloat(3, value);
  @$pb.TagNumber(4)
  $core.bool hasTemperatureC() => $_has(3);
  @$pb.TagNumber(4)
  void clearTemperatureC() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.bool get recording => $_getBF(4);
  @$pb.TagNumber(5)
  set recording($core.bool value) => $_setBool(4, value);
  @$pb.TagNumber(5)
  $core.bool hasRecording() => $_has(4);
  @$pb.TagNumber(5)
  void clearRecording() => $_clearField(5);

  /// Self-reported clock-sync state (clock_synchronization.md). The node computes these
  /// from its own ClockSyncRequest/Reply exchanges; carrying them here is what lets the
  /// Scheduler (scheduler.md) read a per-node offset/uncertainty estimate without the
  /// server needing its own copy of t3 (which only the node observes).
  @$pb.TagNumber(6)
  $fixnum.Int64 get clockOffsetMs => $_getI64(5);
  @$pb.TagNumber(6)
  set clockOffsetMs($fixnum.Int64 value) => $_setInt64(5, value);
  @$pb.TagNumber(6)
  $core.bool hasClockOffsetMs() => $_has(5);
  @$pb.TagNumber(6)
  void clearClockOffsetMs() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.int get clockUncertaintyMs => $_getIZ(6);
  @$pb.TagNumber(7)
  set clockUncertaintyMs($core.int value) => $_setUnsignedInt32(6, value);
  @$pb.TagNumber(7)
  $core.bool hasClockUncertaintyMs() => $_has(6);
  @$pb.TagNumber(7)
  void clearClockUncertaintyMs() => $_clearField(7);

  /// Self-reported RTT from the node's own clock-sync exchanges (clock_synchronization.md
  /// §Exchange algorithm). Bootstraps ConnectionManager's RTT metric on the very first
  /// heartbeat, before any ScheduledCommand/Ack round trip has happened - without this,
  /// a freshly connected node would have no RTT sample and the Scheduler would always
  /// exclude it from the first command (scheduler.md §Algorithm step 3).
  @$pb.TagNumber(8)
  $core.double get lastRttMs => $_getN(7);
  @$pb.TagNumber(8)
  set lastRttMs($core.double value) => $_setFloat(7, value);
  @$pb.TagNumber(8)
  $core.bool hasLastRttMs() => $_has(7);
  @$pb.TagNumber(8)
  void clearLastRttMs() => $_clearField(8);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
