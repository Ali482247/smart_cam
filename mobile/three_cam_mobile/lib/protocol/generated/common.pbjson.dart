// This is a generated file - do not edit.
//
// Generated from common.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports
// ignore_for_file: unused_import

import 'dart:convert' as $convert;
import 'dart:core' as $core;
import 'dart:typed_data' as $typed_data;

@$core.Deprecated('Use resultCodeDescriptor instead')
const ResultCode$json = {
  '1': 'ResultCode',
  '2': [
    {'1': 'RESULT_OK', '2': 0},
    {'1': 'RESULT_REJECTED', '2': 1},
    {'1': 'RESULT_ALREADY_DONE', '2': 2},
    {'1': 'RESULT_ERROR', '2': 3},
  ],
};

/// Descriptor for `ResultCode`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List resultCodeDescriptor = $convert.base64Decode(
    'CgpSZXN1bHRDb2RlEg0KCVJFU1VMVF9PSxAAEhMKD1JFU1VMVF9SRUpFQ1RFRBABEhcKE1JFU1'
    'VMVF9BTFJFQURZX0RPTkUQAhIQCgxSRVNVTFRfRVJST1IQAw==');
