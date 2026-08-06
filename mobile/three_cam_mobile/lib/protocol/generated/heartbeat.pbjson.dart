// This is a generated file - do not edit.
//
// Generated from heartbeat.proto.

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

@$core.Deprecated('Use heartbeatDescriptor instead')
const Heartbeat$json = {
  '1': 'Heartbeat',
  '2': [
    {'1': 'battery_pct', '3': 1, '4': 1, '5': 2, '10': 'batteryPct'},
    {
      '1': 'free_storage_bytes',
      '3': 2,
      '4': 1,
      '5': 4,
      '10': 'freeStorageBytes'
    },
    {
      '1': 'total_storage_bytes',
      '3': 3,
      '4': 1,
      '5': 4,
      '10': 'totalStorageBytes'
    },
    {'1': 'temperature_c', '3': 4, '4': 1, '5': 2, '10': 'temperatureC'},
    {'1': 'recording', '3': 5, '4': 1, '5': 8, '10': 'recording'},
    {'1': 'clock_offset_ms', '3': 6, '4': 1, '5': 3, '10': 'clockOffsetMs'},
    {
      '1': 'clock_uncertainty_ms',
      '3': 7,
      '4': 1,
      '5': 13,
      '10': 'clockUncertaintyMs'
    },
    {'1': 'last_rtt_ms', '3': 8, '4': 1, '5': 2, '10': 'lastRttMs'},
  ],
};

/// Descriptor for `Heartbeat`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List heartbeatDescriptor = $convert.base64Decode(
    'CglIZWFydGJlYXQSHwoLYmF0dGVyeV9wY3QYASABKAJSCmJhdHRlcnlQY3QSLAoSZnJlZV9zdG'
    '9yYWdlX2J5dGVzGAIgASgEUhBmcmVlU3RvcmFnZUJ5dGVzEi4KE3RvdGFsX3N0b3JhZ2VfYnl0'
    'ZXMYAyABKARSEXRvdGFsU3RvcmFnZUJ5dGVzEiMKDXRlbXBlcmF0dXJlX2MYBCABKAJSDHRlbX'
    'BlcmF0dXJlQxIcCglyZWNvcmRpbmcYBSABKAhSCXJlY29yZGluZxImCg9jbG9ja19vZmZzZXRf'
    'bXMYBiABKANSDWNsb2NrT2Zmc2V0TXMSMAoUY2xvY2tfdW5jZXJ0YWludHlfbXMYByABKA1SEm'
    'Nsb2NrVW5jZXJ0YWludHlNcxIeCgtsYXN0X3J0dF9tcxgIIAEoAlIJbGFzdFJ0dE1z');
