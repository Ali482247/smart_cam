// This is a generated file - do not edit.
//
// Generated from envelope.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;

import 'device.pb.dart' as $0;
import 'heartbeat.pb.dart' as $1;
import 'recording.pb.dart' as $3;
import 'scheduler.pb.dart' as $2;
import 'upload.pb.dart' as $4;

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

enum Envelope_Payload {
  hello,
  welcome,
  heartbeat,
  clockReq,
  clockReply,
  schedCmd,
  ack,
  status,
  event,
  uploadTicket,
  uploadProgress,
  heartbeatAck,
  notSet
}

/// Every message, in both directions, is wrapped in exactly one Envelope
/// (protocol_specification.md §Envelope). Binary-serialized, sent as a single WS
/// binary frame — never JSON, never text frames.
class Envelope extends $pb.GeneratedMessage {
  factory Envelope({
    $core.int? protocolVersion,
    $core.String? appVersion,
    $core.String? deviceId,
    $core.String? sessionId,
    $fixnum.Int64? sequenceNumber,
    $fixnum.Int64? timestampMs,
    $0.Hello? hello,
    $0.Welcome? welcome,
    $1.Heartbeat? heartbeat,
    $2.ClockSyncRequest? clockReq,
    $2.ClockSyncReply? clockReply,
    $2.ScheduledCommand? schedCmd,
    $2.Ack? ack,
    $3.StatusUpdate? status,
    $3.Event? event,
    $4.UploadTicket? uploadTicket,
    $4.UploadProgress? uploadProgress,
    $1.HeartbeatAck? heartbeatAck,
  }) {
    final result = create();
    if (protocolVersion != null) result.protocolVersion = protocolVersion;
    if (appVersion != null) result.appVersion = appVersion;
    if (deviceId != null) result.deviceId = deviceId;
    if (sessionId != null) result.sessionId = sessionId;
    if (sequenceNumber != null) result.sequenceNumber = sequenceNumber;
    if (timestampMs != null) result.timestampMs = timestampMs;
    if (hello != null) result.hello = hello;
    if (welcome != null) result.welcome = welcome;
    if (heartbeat != null) result.heartbeat = heartbeat;
    if (clockReq != null) result.clockReq = clockReq;
    if (clockReply != null) result.clockReply = clockReply;
    if (schedCmd != null) result.schedCmd = schedCmd;
    if (ack != null) result.ack = ack;
    if (status != null) result.status = status;
    if (event != null) result.event = event;
    if (uploadTicket != null) result.uploadTicket = uploadTicket;
    if (uploadProgress != null) result.uploadProgress = uploadProgress;
    if (heartbeatAck != null) result.heartbeatAck = heartbeatAck;
    return result;
  }

  Envelope._();

  factory Envelope.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Envelope.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static const $core.Map<$core.int, Envelope_Payload> _Envelope_PayloadByTag = {
    10: Envelope_Payload.hello,
    11: Envelope_Payload.welcome,
    12: Envelope_Payload.heartbeat,
    13: Envelope_Payload.clockReq,
    14: Envelope_Payload.clockReply,
    15: Envelope_Payload.schedCmd,
    16: Envelope_Payload.ack,
    17: Envelope_Payload.status,
    18: Envelope_Payload.event,
    19: Envelope_Payload.uploadTicket,
    20: Envelope_Payload.uploadProgress,
    21: Envelope_Payload.heartbeatAck,
    0: Envelope_Payload.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Envelope',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'threecam.v1'),
      createEmptyInstance: create)
    ..oo(0, [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21])
    ..aI(1, _omitFieldNames ? '' : 'protocolVersion',
        fieldType: $pb.PbFieldType.OU3)
    ..aOS(2, _omitFieldNames ? '' : 'appVersion')
    ..aOS(3, _omitFieldNames ? '' : 'deviceId')
    ..aOS(4, _omitFieldNames ? '' : 'sessionId')
    ..a<$fixnum.Int64>(
        5, _omitFieldNames ? '' : 'sequenceNumber', $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..aInt64(6, _omitFieldNames ? '' : 'timestampMs')
    ..aOM<$0.Hello>(10, _omitFieldNames ? '' : 'hello',
        subBuilder: $0.Hello.create)
    ..aOM<$0.Welcome>(11, _omitFieldNames ? '' : 'welcome',
        subBuilder: $0.Welcome.create)
    ..aOM<$1.Heartbeat>(12, _omitFieldNames ? '' : 'heartbeat',
        subBuilder: $1.Heartbeat.create)
    ..aOM<$2.ClockSyncRequest>(13, _omitFieldNames ? '' : 'clockReq',
        subBuilder: $2.ClockSyncRequest.create)
    ..aOM<$2.ClockSyncReply>(14, _omitFieldNames ? '' : 'clockReply',
        subBuilder: $2.ClockSyncReply.create)
    ..aOM<$2.ScheduledCommand>(15, _omitFieldNames ? '' : 'schedCmd',
        subBuilder: $2.ScheduledCommand.create)
    ..aOM<$2.Ack>(16, _omitFieldNames ? '' : 'ack', subBuilder: $2.Ack.create)
    ..aOM<$3.StatusUpdate>(17, _omitFieldNames ? '' : 'status',
        subBuilder: $3.StatusUpdate.create)
    ..aOM<$3.Event>(18, _omitFieldNames ? '' : 'event',
        subBuilder: $3.Event.create)
    ..aOM<$4.UploadTicket>(19, _omitFieldNames ? '' : 'uploadTicket',
        subBuilder: $4.UploadTicket.create)
    ..aOM<$4.UploadProgress>(20, _omitFieldNames ? '' : 'uploadProgress',
        subBuilder: $4.UploadProgress.create)
    ..aOM<$1.HeartbeatAck>(21, _omitFieldNames ? '' : 'heartbeatAck',
        subBuilder: $1.HeartbeatAck.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Envelope clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Envelope copyWith(void Function(Envelope) updates) =>
      super.copyWith((message) => updates(message as Envelope)) as Envelope;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Envelope create() => Envelope._();
  @$core.override
  Envelope createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static Envelope getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Envelope>(create);
  static Envelope? _defaultInstance;

  @$pb.TagNumber(10)
  @$pb.TagNumber(11)
  @$pb.TagNumber(12)
  @$pb.TagNumber(13)
  @$pb.TagNumber(14)
  @$pb.TagNumber(15)
  @$pb.TagNumber(16)
  @$pb.TagNumber(17)
  @$pb.TagNumber(18)
  @$pb.TagNumber(19)
  @$pb.TagNumber(20)
  @$pb.TagNumber(21)
  Envelope_Payload whichPayload() => _Envelope_PayloadByTag[$_whichOneof(0)]!;
  @$pb.TagNumber(10)
  @$pb.TagNumber(11)
  @$pb.TagNumber(12)
  @$pb.TagNumber(13)
  @$pb.TagNumber(14)
  @$pb.TagNumber(15)
  @$pb.TagNumber(16)
  @$pb.TagNumber(17)
  @$pb.TagNumber(18)
  @$pb.TagNumber(19)
  @$pb.TagNumber(20)
  @$pb.TagNumber(21)
  void clearPayload() => $_clearField($_whichOneof(0));

  @$pb.TagNumber(1)
  $core.int get protocolVersion => $_getIZ(0);
  @$pb.TagNumber(1)
  set protocolVersion($core.int value) => $_setUnsignedInt32(0, value);
  @$pb.TagNumber(1)
  $core.bool hasProtocolVersion() => $_has(0);
  @$pb.TagNumber(1)
  void clearProtocolVersion() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get appVersion => $_getSZ(1);
  @$pb.TagNumber(2)
  set appVersion($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasAppVersion() => $_has(1);
  @$pb.TagNumber(2)
  void clearAppVersion() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get deviceId => $_getSZ(2);
  @$pb.TagNumber(3)
  set deviceId($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasDeviceId() => $_has(2);
  @$pb.TagNumber(3)
  void clearDeviceId() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get sessionId => $_getSZ(3);
  @$pb.TagNumber(4)
  set sessionId($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasSessionId() => $_has(3);
  @$pb.TagNumber(4)
  void clearSessionId() => $_clearField(4);

  @$pb.TagNumber(5)
  $fixnum.Int64 get sequenceNumber => $_getI64(4);
  @$pb.TagNumber(5)
  set sequenceNumber($fixnum.Int64 value) => $_setInt64(4, value);
  @$pb.TagNumber(5)
  $core.bool hasSequenceNumber() => $_has(4);
  @$pb.TagNumber(5)
  void clearSequenceNumber() => $_clearField(5);

  @$pb.TagNumber(6)
  $fixnum.Int64 get timestampMs => $_getI64(5);
  @$pb.TagNumber(6)
  set timestampMs($fixnum.Int64 value) => $_setInt64(5, value);
  @$pb.TagNumber(6)
  $core.bool hasTimestampMs() => $_has(5);
  @$pb.TagNumber(6)
  void clearTimestampMs() => $_clearField(6);

  @$pb.TagNumber(10)
  $0.Hello get hello => $_getN(6);
  @$pb.TagNumber(10)
  set hello($0.Hello value) => $_setField(10, value);
  @$pb.TagNumber(10)
  $core.bool hasHello() => $_has(6);
  @$pb.TagNumber(10)
  void clearHello() => $_clearField(10);
  @$pb.TagNumber(10)
  $0.Hello ensureHello() => $_ensure(6);

  @$pb.TagNumber(11)
  $0.Welcome get welcome => $_getN(7);
  @$pb.TagNumber(11)
  set welcome($0.Welcome value) => $_setField(11, value);
  @$pb.TagNumber(11)
  $core.bool hasWelcome() => $_has(7);
  @$pb.TagNumber(11)
  void clearWelcome() => $_clearField(11);
  @$pb.TagNumber(11)
  $0.Welcome ensureWelcome() => $_ensure(7);

  @$pb.TagNumber(12)
  $1.Heartbeat get heartbeat => $_getN(8);
  @$pb.TagNumber(12)
  set heartbeat($1.Heartbeat value) => $_setField(12, value);
  @$pb.TagNumber(12)
  $core.bool hasHeartbeat() => $_has(8);
  @$pb.TagNumber(12)
  void clearHeartbeat() => $_clearField(12);
  @$pb.TagNumber(12)
  $1.Heartbeat ensureHeartbeat() => $_ensure(8);

  @$pb.TagNumber(13)
  $2.ClockSyncRequest get clockReq => $_getN(9);
  @$pb.TagNumber(13)
  set clockReq($2.ClockSyncRequest value) => $_setField(13, value);
  @$pb.TagNumber(13)
  $core.bool hasClockReq() => $_has(9);
  @$pb.TagNumber(13)
  void clearClockReq() => $_clearField(13);
  @$pb.TagNumber(13)
  $2.ClockSyncRequest ensureClockReq() => $_ensure(9);

  @$pb.TagNumber(14)
  $2.ClockSyncReply get clockReply => $_getN(10);
  @$pb.TagNumber(14)
  set clockReply($2.ClockSyncReply value) => $_setField(14, value);
  @$pb.TagNumber(14)
  $core.bool hasClockReply() => $_has(10);
  @$pb.TagNumber(14)
  void clearClockReply() => $_clearField(14);
  @$pb.TagNumber(14)
  $2.ClockSyncReply ensureClockReply() => $_ensure(10);

  @$pb.TagNumber(15)
  $2.ScheduledCommand get schedCmd => $_getN(11);
  @$pb.TagNumber(15)
  set schedCmd($2.ScheduledCommand value) => $_setField(15, value);
  @$pb.TagNumber(15)
  $core.bool hasSchedCmd() => $_has(11);
  @$pb.TagNumber(15)
  void clearSchedCmd() => $_clearField(15);
  @$pb.TagNumber(15)
  $2.ScheduledCommand ensureSchedCmd() => $_ensure(11);

  @$pb.TagNumber(16)
  $2.Ack get ack => $_getN(12);
  @$pb.TagNumber(16)
  set ack($2.Ack value) => $_setField(16, value);
  @$pb.TagNumber(16)
  $core.bool hasAck() => $_has(12);
  @$pb.TagNumber(16)
  void clearAck() => $_clearField(16);
  @$pb.TagNumber(16)
  $2.Ack ensureAck() => $_ensure(12);

  @$pb.TagNumber(17)
  $3.StatusUpdate get status => $_getN(13);
  @$pb.TagNumber(17)
  set status($3.StatusUpdate value) => $_setField(17, value);
  @$pb.TagNumber(17)
  $core.bool hasStatus() => $_has(13);
  @$pb.TagNumber(17)
  void clearStatus() => $_clearField(17);
  @$pb.TagNumber(17)
  $3.StatusUpdate ensureStatus() => $_ensure(13);

  @$pb.TagNumber(18)
  $3.Event get event => $_getN(14);
  @$pb.TagNumber(18)
  set event($3.Event value) => $_setField(18, value);
  @$pb.TagNumber(18)
  $core.bool hasEvent() => $_has(14);
  @$pb.TagNumber(18)
  void clearEvent() => $_clearField(18);
  @$pb.TagNumber(18)
  $3.Event ensureEvent() => $_ensure(14);

  @$pb.TagNumber(19)
  $4.UploadTicket get uploadTicket => $_getN(15);
  @$pb.TagNumber(19)
  set uploadTicket($4.UploadTicket value) => $_setField(19, value);
  @$pb.TagNumber(19)
  $core.bool hasUploadTicket() => $_has(15);
  @$pb.TagNumber(19)
  void clearUploadTicket() => $_clearField(19);
  @$pb.TagNumber(19)
  $4.UploadTicket ensureUploadTicket() => $_ensure(15);

  @$pb.TagNumber(20)
  $4.UploadProgress get uploadProgress => $_getN(16);
  @$pb.TagNumber(20)
  set uploadProgress($4.UploadProgress value) => $_setField(20, value);
  @$pb.TagNumber(20)
  $core.bool hasUploadProgress() => $_has(16);
  @$pb.TagNumber(20)
  void clearUploadProgress() => $_clearField(20);
  @$pb.TagNumber(20)
  $4.UploadProgress ensureUploadProgress() => $_ensure(16);

  @$pb.TagNumber(21)
  $1.HeartbeatAck get heartbeatAck => $_getN(17);
  @$pb.TagNumber(21)
  set heartbeatAck($1.HeartbeatAck value) => $_setField(21, value);
  @$pb.TagNumber(21)
  $core.bool hasHeartbeatAck() => $_has(17);
  @$pb.TagNumber(21)
  void clearHeartbeatAck() => $_clearField(21);
  @$pb.TagNumber(21)
  $1.HeartbeatAck ensureHeartbeatAck() => $_ensure(17);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
