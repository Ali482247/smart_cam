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

import 'package:protobuf/protobuf.dart' as $pb;

class ScheduledCommand_Type extends $pb.ProtobufEnum {
  static const ScheduledCommand_Type START =
      ScheduledCommand_Type._(0, _omitEnumNames ? '' : 'START');
  static const ScheduledCommand_Type STOP =
      ScheduledCommand_Type._(1, _omitEnumNames ? '' : 'STOP');
  static const ScheduledCommand_Type TOGGLE =
      ScheduledCommand_Type._(2, _omitEnumNames ? '' : 'TOGGLE');

  static const $core.List<ScheduledCommand_Type> values =
      <ScheduledCommand_Type>[
    START,
    STOP,
    TOGGLE,
  ];

  static final $core.List<ScheduledCommand_Type?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 2);
  static ScheduledCommand_Type? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const ScheduledCommand_Type._(super.value, super.name);
}

const $core.bool _omitEnumNames =
    $core.bool.fromEnvironment('protobuf.omit_enum_names');
