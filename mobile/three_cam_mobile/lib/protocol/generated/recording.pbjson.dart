// This is a generated file - do not edit.
//
// Generated from recording.proto.

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

@$core.Deprecated('Use statusUpdateDescriptor instead')
const StatusUpdate$json = {
  '1': 'StatusUpdate',
  '2': [
    {'1': 'recording', '3': 1, '4': 1, '5': 8, '10': 'recording'},
    {'1': 'actual_fps', '3': 2, '4': 1, '5': 2, '10': 'actualFps'},
    {'1': 'active_video_name', '3': 3, '4': 1, '5': 9, '10': 'activeVideoName'},
    {
      '1': 'recording_started_at_ms',
      '3': 4,
      '4': 1,
      '5': 3,
      '10': 'recordingStartedAtMs'
    },
  ],
};

/// Descriptor for `StatusUpdate`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List statusUpdateDescriptor = $convert.base64Decode(
    'CgxTdGF0dXNVcGRhdGUSHAoJcmVjb3JkaW5nGAEgASgIUglyZWNvcmRpbmcSHQoKYWN0dWFsX2'
    'ZwcxgCIAEoAlIJYWN0dWFsRnBzEioKEWFjdGl2ZV92aWRlb19uYW1lGAMgASgJUg9hY3RpdmVW'
    'aWRlb05hbWUSNQoXcmVjb3JkaW5nX3N0YXJ0ZWRfYXRfbXMYBCABKANSFHJlY29yZGluZ1N0YX'
    'J0ZWRBdE1z');

@$core.Deprecated('Use eventDescriptor instead')
const Event$json = {
  '1': 'Event',
  '2': [
    {
      '1': 'type',
      '3': 1,
      '4': 1,
      '5': 14,
      '6': '.threecam.v1.Event.Type',
      '10': 'type'
    },
    {'1': 'detail', '3': 2, '4': 1, '5': 9, '10': 'detail'},
  ],
  '4': [Event_Type$json],
};

@$core.Deprecated('Use eventDescriptor instead')
const Event_Type$json = {
  '1': 'Type',
  '2': [
    {'1': 'DEVICE_CONNECTED', '2': 0},
    {'1': 'DEVICE_DISCONNECTED', '2': 1},
    {'1': 'RECORDING_STARTED', '2': 2},
    {'1': 'RECORDING_STOPPED', '2': 3},
    {'1': 'UPLOAD_STARTED', '2': 4},
    {'1': 'UPLOAD_COMPLETED', '2': 5},
    {'1': 'STORAGE_WARNING', '2': 6},
    {'1': 'BATTERY_WARNING', '2': 7},
    {'1': 'CONNECTION_LOST', '2': 8},
  ],
};

/// Descriptor for `Event`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List eventDescriptor = $convert.base64Decode(
    'CgVFdmVudBIrCgR0eXBlGAEgASgOMhcudGhyZWVjYW0udjEuRXZlbnQuVHlwZVIEdHlwZRIWCg'
    'ZkZXRhaWwYAiABKAlSBmRldGFpbCLMAQoEVHlwZRIUChBERVZJQ0VfQ09OTkVDVEVEEAASFwoT'
    'REVWSUNFX0RJU0NPTk5FQ1RFRBABEhUKEVJFQ09SRElOR19TVEFSVEVEEAISFQoRUkVDT1JESU'
    '5HX1NUT1BQRUQQAxISCg5VUExPQURfU1RBUlRFRBAEEhQKEFVQTE9BRF9DT01QTEVURUQQBRIT'
    'Cg9TVE9SQUdFX1dBUk5JTkcQBhITCg9CQVRURVJZX1dBUk5JTkcQBxITCg9DT05ORUNUSU9OX0'
    'xPU1QQCA==');
