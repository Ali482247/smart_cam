import 'dart:math' as math;

import 'package:fixnum/fixnum.dart';

import '../protocol/generated/scheduler.pb.dart';

class ClockSyncEstimate {
  const ClockSyncEstimate({required this.offsetMs, required this.uncertaintyMs});

  final double offsetMs;
  final double uncertaintyMs;

  static const unknown = ClockSyncEstimate(offsetMs: 0, uncertaintyMs: double.infinity);
}

class _OffsetSample {
  const _OffsetSample(this.offsetMs, this.rttMs);
  final double offsetMs;
  final double rttMs;
}

typedef ClockSyncExchange = Future<ClockSyncReply> Function(ClockSyncRequest request);

class ClockSyncSampler {
  /// [nowMs] is injectable so tests can drive t0/t3 deterministically instead of
  /// depending on real wall-clock delays between send and receive.
  ClockSyncSampler(this._exchange, {int Function()? nowMs})
      : _nowMs = nowMs ?? (() => DateTime.now().millisecondsSinceEpoch);

  final ClockSyncExchange _exchange;
  final int Function() _nowMs;
  ClockSyncEstimate _latest = ClockSyncEstimate.unknown;
  double? _lastRttMs;

  ClockSyncEstimate get latest => _latest;
  double? get lastRttMs => _lastRttMs;

  /// Sampling strategy (clock_synchronization.md §Sampling strategy): a burst of
  /// [count] samples spaced [spacing] apart, outliers (RTT > 1.5x median) discarded,
  /// remaining offsets averaged.
  Future<ClockSyncEstimate> sampleBurst({
    int count = 8,
    Duration spacing = const Duration(milliseconds: 200),
  }) async {
    final samples = <_OffsetSample>[];
    for (var i = 0; i < count; i++) {
      final sample = await _sampleOnce();
      if (sample != null) samples.add(sample);
      if (i < count - 1) {
        await Future.delayed(spacing);
      }
    }
    _latest = _reduce(samples);
    return _latest;
  }

  Future<_OffsetSample?> _sampleOnce() async {
    final t0 = _nowMs();
    ClockSyncReply reply;
    try {
      reply = await _exchange(ClockSyncRequest(t0Ms: Int64(t0)));
    } catch (_) {
      return null;
    }
    final t3 = _nowMs();
    final t1 = reply.t1Ms.toInt();
    final t2 = reply.t2Ms.toInt();

    final rttMs = (t3 - t0) - (t2 - t1);
    final offsetMs = ((t1 - t0) + (t2 - t3)) / 2;
    _lastRttMs = rttMs.toDouble();
    return _OffsetSample(offsetMs, rttMs.toDouble());
  }

  ClockSyncEstimate _reduce(List<_OffsetSample> samples) {
    if (samples.isEmpty) return _latest;

    final sortedRtt = samples.map((s) => s.rttMs).toList()..sort();
    final medianRtt = sortedRtt[sortedRtt.length ~/ 2];
    final threshold = medianRtt * 1.5;
    final kept = samples.where((s) => s.rttMs <= threshold).toList();
    final use = kept.isEmpty ? samples : kept;

    final avgOffset = use.map((s) => s.offsetMs).reduce((a, b) => a + b) / use.length;
    final offsets = use.map((s) => s.offsetMs);
    final uncertaintyMs = (offsets.reduce(math.max) - offsets.reduce(math.min)) / 2;

    return ClockSyncEstimate(offsetMs: avgOffset, uncertaintyMs: uncertaintyMs);
  }

  /// `execute_at_ms` is on the server's clock; converts to this node's local clock
  /// using the current offset estimate (clock_synchronization.md §Applying the offset).
  int serverTimeToLocalMs(int executeAtMs) => (executeAtMs - _latest.offsetMs).round();
}
