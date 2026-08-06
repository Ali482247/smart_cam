// This is a generated file - do not edit.
//
// Generated from envelope.proto.

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

@$core.Deprecated('Use envelopeDescriptor instead')
const Envelope$json = {
  '1': 'Envelope',
  '2': [
    {'1': 'protocol_version', '3': 1, '4': 1, '5': 13, '10': 'protocolVersion'},
    {'1': 'app_version', '3': 2, '4': 1, '5': 9, '10': 'appVersion'},
    {'1': 'device_id', '3': 3, '4': 1, '5': 9, '10': 'deviceId'},
    {'1': 'session_id', '3': 4, '4': 1, '5': 9, '10': 'sessionId'},
    {'1': 'sequence_number', '3': 5, '4': 1, '5': 4, '10': 'sequenceNumber'},
    {'1': 'timestamp_ms', '3': 6, '4': 1, '5': 3, '10': 'timestampMs'},
    {
      '1': 'hello',
      '3': 10,
      '4': 1,
      '5': 11,
      '6': '.threecam.v1.Hello',
      '9': 0,
      '10': 'hello'
    },
    {
      '1': 'welcome',
      '3': 11,
      '4': 1,
      '5': 11,
      '6': '.threecam.v1.Welcome',
      '9': 0,
      '10': 'welcome'
    },
    {
      '1': 'heartbeat',
      '3': 12,
      '4': 1,
      '5': 11,
      '6': '.threecam.v1.Heartbeat',
      '9': 0,
      '10': 'heartbeat'
    },
    {
      '1': 'clock_req',
      '3': 13,
      '4': 1,
      '5': 11,
      '6': '.threecam.v1.ClockSyncRequest',
      '9': 0,
      '10': 'clockReq'
    },
    {
      '1': 'clock_reply',
      '3': 14,
      '4': 1,
      '5': 11,
      '6': '.threecam.v1.ClockSyncReply',
      '9': 0,
      '10': 'clockReply'
    },
    {
      '1': 'sched_cmd',
      '3': 15,
      '4': 1,
      '5': 11,
      '6': '.threecam.v1.ScheduledCommand',
      '9': 0,
      '10': 'schedCmd'
    },
    {
      '1': 'ack',
      '3': 16,
      '4': 1,
      '5': 11,
      '6': '.threecam.v1.Ack',
      '9': 0,
      '10': 'ack'
    },
    {
      '1': 'status',
      '3': 17,
      '4': 1,
      '5': 11,
      '6': '.threecam.v1.StatusUpdate',
      '9': 0,
      '10': 'status'
    },
    {
      '1': 'event',
      '3': 18,
      '4': 1,
      '5': 11,
      '6': '.threecam.v1.Event',
      '9': 0,
      '10': 'event'
    },
    {
      '1': 'upload_ticket',
      '3': 19,
      '4': 1,
      '5': 11,
      '6': '.threecam.v1.UploadTicket',
      '9': 0,
      '10': 'uploadTicket'
    },
    {
      '1': 'upload_progress',
      '3': 20,
      '4': 1,
      '5': 11,
      '6': '.threecam.v1.UploadProgress',
      '9': 0,
      '10': 'uploadProgress'
    },
  ],
  '8': [
    {'1': 'payload'},
  ],
};

/// Descriptor for `Envelope`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List envelopeDescriptor = $convert.base64Decode(
    'CghFbnZlbG9wZRIpChBwcm90b2NvbF92ZXJzaW9uGAEgASgNUg9wcm90b2NvbFZlcnNpb24SHw'
    'oLYXBwX3ZlcnNpb24YAiABKAlSCmFwcFZlcnNpb24SGwoJZGV2aWNlX2lkGAMgASgJUghkZXZp'
    'Y2VJZBIdCgpzZXNzaW9uX2lkGAQgASgJUglzZXNzaW9uSWQSJwoPc2VxdWVuY2VfbnVtYmVyGA'
    'UgASgEUg5zZXF1ZW5jZU51bWJlchIhCgx0aW1lc3RhbXBfbXMYBiABKANSC3RpbWVzdGFtcE1z'
    'EioKBWhlbGxvGAogASgLMhIudGhyZWVjYW0udjEuSGVsbG9IAFIFaGVsbG8SMAoHd2VsY29tZR'
    'gLIAEoCzIULnRocmVlY2FtLnYxLldlbGNvbWVIAFIHd2VsY29tZRI2CgloZWFydGJlYXQYDCAB'
    'KAsyFi50aHJlZWNhbS52MS5IZWFydGJlYXRIAFIJaGVhcnRiZWF0EjwKCWNsb2NrX3JlcRgNIA'
    'EoCzIdLnRocmVlY2FtLnYxLkNsb2NrU3luY1JlcXVlc3RIAFIIY2xvY2tSZXESPgoLY2xvY2tf'
    'cmVwbHkYDiABKAsyGy50aHJlZWNhbS52MS5DbG9ja1N5bmNSZXBseUgAUgpjbG9ja1JlcGx5Ej'
    'wKCXNjaGVkX2NtZBgPIAEoCzIdLnRocmVlY2FtLnYxLlNjaGVkdWxlZENvbW1hbmRIAFIIc2No'
    'ZWRDbWQSJAoDYWNrGBAgASgLMhAudGhyZWVjYW0udjEuQWNrSABSA2FjaxIzCgZzdGF0dXMYES'
    'ABKAsyGS50aHJlZWNhbS52MS5TdGF0dXNVcGRhdGVIAFIGc3RhdHVzEioKBWV2ZW50GBIgASgL'
    'MhIudGhyZWVjYW0udjEuRXZlbnRIAFIFZXZlbnQSQAoNdXBsb2FkX3RpY2tldBgTIAEoCzIZLn'
    'RocmVlY2FtLnYxLlVwbG9hZFRpY2tldEgAUgx1cGxvYWRUaWNrZXQSRgoPdXBsb2FkX3Byb2dy'
    'ZXNzGBQgASgLMhsudGhyZWVjYW0udjEuVXBsb2FkUHJvZ3Jlc3NIAFIOdXBsb2FkUHJvZ3Jlc3'
    'NCCQoHcGF5bG9hZA==');
