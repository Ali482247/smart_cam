// This is a generated file - do not edit.
//
// Generated from common.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

class ResultCode extends $pb.ProtobufEnum {
  static const ResultCode RESULT_OK =
      ResultCode._(0, _omitEnumNames ? '' : 'RESULT_OK');
  static const ResultCode RESULT_REJECTED =
      ResultCode._(1, _omitEnumNames ? '' : 'RESULT_REJECTED');
  static const ResultCode RESULT_ALREADY_DONE =
      ResultCode._(2, _omitEnumNames ? '' : 'RESULT_ALREADY_DONE');
  static const ResultCode RESULT_ERROR =
      ResultCode._(3, _omitEnumNames ? '' : 'RESULT_ERROR');

  static const $core.List<ResultCode> values = <ResultCode>[
    RESULT_OK,
    RESULT_REJECTED,
    RESULT_ALREADY_DONE,
    RESULT_ERROR,
  ];

  static final $core.List<ResultCode?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 3);
  static ResultCode? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const ResultCode._(super.value, super.name);
}

const $core.bool _omitEnumNames =
    $core.bool.fromEnvironment('protobuf.omit_enum_names');
