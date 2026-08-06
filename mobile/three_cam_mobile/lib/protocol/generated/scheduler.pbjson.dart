// This is a generated file - do not edit.
//
// Generated from scheduler.proto.

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

@$core.Deprecated('Use clockSyncRequestDescriptor instead')
const ClockSyncRequest$json = {
  '1': 'ClockSyncRequest',
  '2': [
    {'1': 't0_ms', '3': 1, '4': 1, '5': 3, '10': 't0Ms'},
  ],
};

/// Descriptor for `ClockSyncRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List clockSyncRequestDescriptor = $convert
    .base64Decode('ChBDbG9ja1N5bmNSZXF1ZXN0EhMKBXQwX21zGAEgASgDUgR0ME1z');

@$core.Deprecated('Use clockSyncReplyDescriptor instead')
const ClockSyncReply$json = {
  '1': 'ClockSyncReply',
  '2': [
    {'1': 't0_ms', '3': 1, '4': 1, '5': 3, '10': 't0Ms'},
    {'1': 't1_ms', '3': 2, '4': 1, '5': 3, '10': 't1Ms'},
    {'1': 't2_ms', '3': 3, '4': 1, '5': 3, '10': 't2Ms'},
  ],
};

/// Descriptor for `ClockSyncReply`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List clockSyncReplyDescriptor = $convert.base64Decode(
    'Cg5DbG9ja1N5bmNSZXBseRITCgV0MF9tcxgBIAEoA1IEdDBNcxITCgV0MV9tcxgCIAEoA1IEdD'
    'FNcxITCgV0Ml9tcxgDIAEoA1IEdDJNcw==');

@$core.Deprecated('Use scheduledCommandDescriptor instead')
const ScheduledCommand$json = {
  '1': 'ScheduledCommand',
  '2': [
    {
      '1': 'type',
      '3': 1,
      '4': 1,
      '5': 14,
      '6': '.threecam.v1.ScheduledCommand.Type',
      '10': 'type'
    },
    {'1': 'execute_at_ms', '3': 2, '4': 1, '5': 3, '10': 'executeAtMs'},
    {'1': 'command_id', '3': 3, '4': 1, '5': 9, '10': 'commandId'},
    {'1': 'camera_name', '3': 4, '4': 1, '5': 9, '10': 'cameraName'},
    {'1': 'session_label', '3': 5, '4': 1, '5': 9, '10': 'sessionLabel'},
    {'1': 'record_index', '3': 6, '4': 1, '5': 13, '10': 'recordIndex'},
  ],
  '4': [ScheduledCommand_Type$json],
};

@$core.Deprecated('Use scheduledCommandDescriptor instead')
const ScheduledCommand_Type$json = {
  '1': 'Type',
  '2': [
    {'1': 'START', '2': 0},
    {'1': 'STOP', '2': 1},
    {'1': 'TOGGLE', '2': 2},
  ],
};

/// Descriptor for `ScheduledCommand`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List scheduledCommandDescriptor = $convert.base64Decode(
    'ChBTY2hlZHVsZWRDb21tYW5kEjYKBHR5cGUYASABKA4yIi50aHJlZWNhbS52MS5TY2hlZHVsZW'
    'RDb21tYW5kLlR5cGVSBHR5cGUSIgoNZXhlY3V0ZV9hdF9tcxgCIAEoA1ILZXhlY3V0ZUF0TXMS'
    'HQoKY29tbWFuZF9pZBgDIAEoCVIJY29tbWFuZElkEh8KC2NhbWVyYV9uYW1lGAQgASgJUgpjYW'
    '1lcmFOYW1lEiMKDXNlc3Npb25fbGFiZWwYBSABKAlSDHNlc3Npb25MYWJlbBIhCgxyZWNvcmRf'
    'aW5kZXgYBiABKA1SC3JlY29yZEluZGV4IicKBFR5cGUSCQoFU1RBUlQQABIICgRTVE9QEAESCg'
    'oGVE9HR0xFEAI=');

@$core.Deprecated('Use ackDescriptor instead')
const Ack$json = {
  '1': 'Ack',
  '2': [
    {'1': 'command_id', '3': 1, '4': 1, '5': 9, '10': 'commandId'},
    {
      '1': 'result',
      '3': 2,
      '4': 1,
      '5': 14,
      '6': '.threecam.v1.ResultCode',
      '10': 'result'
    },
  ],
};

/// Descriptor for `Ack`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ackDescriptor = $convert.base64Decode(
    'CgNBY2sSHQoKY29tbWFuZF9pZBgBIAEoCVIJY29tbWFuZElkEi8KBnJlc3VsdBgCIAEoDjIXLn'
    'RocmVlY2FtLnYxLlJlc3VsdENvZGVSBnJlc3VsdA==');
