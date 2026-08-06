// This is a generated file - do not edit.
//
// Generated from device.proto.

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

@$core.Deprecated('Use helloDescriptor instead')
const Hello$json = {
  '1': 'Hello',
  '2': [
    {'1': 'device_id', '3': 1, '4': 1, '5': 9, '10': 'deviceId'},
    {'1': 'device_name', '3': 2, '4': 1, '5': 9, '10': 'deviceName'},
    {'1': 'manufacturer', '3': 3, '4': 1, '5': 9, '10': 'manufacturer'},
    {'1': 'os_version', '3': 4, '4': 1, '5': 9, '10': 'osVersion'},
    {'1': 'device_slot', '3': 5, '4': 1, '5': 5, '10': 'deviceSlot'},
    {'1': 'device_label', '3': 6, '4': 1, '5': 9, '10': 'deviceLabel'},
    {'1': 'android_id', '3': 7, '4': 1, '5': 9, '10': 'androidId'},
    {'1': 'app_version', '3': 8, '4': 1, '5': 9, '10': 'appVersion'},
  ],
};

/// Descriptor for `Hello`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List helloDescriptor = $convert.base64Decode(
    'CgVIZWxsbxIbCglkZXZpY2VfaWQYASABKAlSCGRldmljZUlkEh8KC2RldmljZV9uYW1lGAIgAS'
    'gJUgpkZXZpY2VOYW1lEiIKDG1hbnVmYWN0dXJlchgDIAEoCVIMbWFudWZhY3R1cmVyEh0KCm9z'
    'X3ZlcnNpb24YBCABKAlSCW9zVmVyc2lvbhIfCgtkZXZpY2Vfc2xvdBgFIAEoBVIKZGV2aWNlU2'
    'xvdBIhCgxkZXZpY2VfbGFiZWwYBiABKAlSC2RldmljZUxhYmVsEh0KCmFuZHJvaWRfaWQYByAB'
    'KAlSCWFuZHJvaWRJZBIfCgthcHBfdmVyc2lvbhgIIAEoCVIKYXBwVmVyc2lvbg==');

@$core.Deprecated('Use welcomeDescriptor instead')
const Welcome$json = {
  '1': 'Welcome',
  '2': [
    {'1': 'session_id', '3': 1, '4': 1, '5': 9, '10': 'sessionId'},
    {'1': 'protocol_version', '3': 2, '4': 1, '5': 13, '10': 'protocolVersion'},
    {'1': 'server_time_ms', '3': 3, '4': 1, '5': 3, '10': 'serverTimeMs'},
    {'1': 'error', '3': 4, '4': 1, '5': 9, '10': 'error'},
  ],
};

/// Descriptor for `Welcome`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List welcomeDescriptor = $convert.base64Decode(
    'CgdXZWxjb21lEh0KCnNlc3Npb25faWQYASABKAlSCXNlc3Npb25JZBIpChBwcm90b2NvbF92ZX'
    'JzaW9uGAIgASgNUg9wcm90b2NvbFZlcnNpb24SJAoOc2VydmVyX3RpbWVfbXMYAyABKANSDHNl'
    'cnZlclRpbWVNcxIUCgVlcnJvchgEIAEoCVIFZXJyb3I=');
