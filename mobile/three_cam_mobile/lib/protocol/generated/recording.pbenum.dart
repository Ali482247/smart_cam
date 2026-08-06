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

import 'package:protobuf/protobuf.dart' as $pb;

class Event_Type extends $pb.ProtobufEnum {
  static const Event_Type DEVICE_CONNECTED =
      Event_Type._(0, _omitEnumNames ? '' : 'DEVICE_CONNECTED');
  static const Event_Type DEVICE_DISCONNECTED =
      Event_Type._(1, _omitEnumNames ? '' : 'DEVICE_DISCONNECTED');
  static const Event_Type RECORDING_STARTED =
      Event_Type._(2, _omitEnumNames ? '' : 'RECORDING_STARTED');
  static const Event_Type RECORDING_STOPPED =
      Event_Type._(3, _omitEnumNames ? '' : 'RECORDING_STOPPED');
  static const Event_Type UPLOAD_STARTED =
      Event_Type._(4, _omitEnumNames ? '' : 'UPLOAD_STARTED');
  static const Event_Type UPLOAD_COMPLETED =
      Event_Type._(5, _omitEnumNames ? '' : 'UPLOAD_COMPLETED');
  static const Event_Type STORAGE_WARNING =
      Event_Type._(6, _omitEnumNames ? '' : 'STORAGE_WARNING');
  static const Event_Type BATTERY_WARNING =
      Event_Type._(7, _omitEnumNames ? '' : 'BATTERY_WARNING');
  static const Event_Type CONNECTION_LOST =
      Event_Type._(8, _omitEnumNames ? '' : 'CONNECTION_LOST');

  static const $core.List<Event_Type> values = <Event_Type>[
    DEVICE_CONNECTED,
    DEVICE_DISCONNECTED,
    RECORDING_STARTED,
    RECORDING_STOPPED,
    UPLOAD_STARTED,
    UPLOAD_COMPLETED,
    STORAGE_WARNING,
    BATTERY_WARNING,
    CONNECTION_LOST,
  ];

  static final $core.List<Event_Type?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 8);
  static Event_Type? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const Event_Type._(super.value, super.name);
}

const $core.bool _omitEnumNames =
    $core.bool.fromEnvironment('protobuf.omit_enum_names');
