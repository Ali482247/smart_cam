// This is a generated file - do not edit.
//
// Generated from upload.proto.

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

@$core.Deprecated('Use uploadTicketDescriptor instead')
const UploadTicket$json = {
  '1': 'UploadTicket',
  '2': [
    {'1': 'video_name', '3': 1, '4': 1, '5': 9, '10': 'videoName'},
    {'1': 'upload_url', '3': 2, '4': 1, '5': 9, '10': 'uploadUrl'},
    {'1': 'upload_token', '3': 3, '4': 1, '5': 9, '10': 'uploadToken'},
  ],
};

/// Descriptor for `UploadTicket`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List uploadTicketDescriptor = $convert.base64Decode(
    'CgxVcGxvYWRUaWNrZXQSHQoKdmlkZW9fbmFtZRgBIAEoCVIJdmlkZW9OYW1lEh0KCnVwbG9hZF'
    '91cmwYAiABKAlSCXVwbG9hZFVybBIhCgx1cGxvYWRfdG9rZW4YAyABKAlSC3VwbG9hZFRva2Vu');

@$core.Deprecated('Use uploadProgressDescriptor instead')
const UploadProgress$json = {
  '1': 'UploadProgress',
  '2': [
    {'1': 'video_name', '3': 1, '4': 1, '5': 9, '10': 'videoName'},
    {'1': 'bytes_sent', '3': 2, '4': 1, '5': 4, '10': 'bytesSent'},
    {'1': 'total_bytes', '3': 3, '4': 1, '5': 4, '10': 'totalBytes'},
  ],
};

/// Descriptor for `UploadProgress`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List uploadProgressDescriptor = $convert.base64Decode(
    'Cg5VcGxvYWRQcm9ncmVzcxIdCgp2aWRlb19uYW1lGAEgASgJUgl2aWRlb05hbWUSHQoKYnl0ZX'
    'Nfc2VudBgCIAEoBFIJYnl0ZXNTZW50Eh8KC3RvdGFsX2J5dGVzGAMgASgEUgp0b3RhbEJ5dGVz');
