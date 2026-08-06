import 'package:fixnum/fixnum.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:three_cam_mobile/protocol/generated/scheduler.pb.dart';
import 'package:three_cam_mobile/ws/clock_sync_sampler.dart';

void main() {
  test('sampleBurst recovers a known clock skew', () async {
    // A fake, fully controlled clock shared between the sampler's t0/t3 reads and the
    // fake exchange - this is what makes the NTP formula testable without depending on
    // real wall-clock delays (see clock_sync_sampler.dart's `nowMs` injection point).
    var clock = 1000000;

    Future<ClockSyncReply> exchange(ClockSyncRequest request) async {
      final t0 = request.t0Ms.toInt();
      final t1 = t0 + 21; // server clock offset (+20) + ~1ms one-way delay
      final t2 = t0 + 23; // +2ms server-side processing
      clock += 4; // total round-trip elapsed on the node's own clock
      return ClockSyncReply(t0Ms: Int64(t0), t1Ms: Int64(t1), t2Ms: Int64(t2));
    }

    final sampler = ClockSyncSampler(exchange, nowMs: () => clock);
    final estimate = await sampler.sampleBurst(count: 3, spacing: Duration.zero);

    // offset = ((t1-t0) + (t2-t3)) / 2 = ((21) + (23-4)) / 2 = 20
    expect(estimate.offsetMs, closeTo(20, 0.001));
    expect(estimate.uncertaintyMs, lessThan(0.001));
  });

  test('sampleBurst discards a high-RTT outlier sample', () async {
    var clock = 1000000;
    var call = 0;

    Future<ClockSyncReply> exchange(ClockSyncRequest request) async {
      call += 1;
      final t0 = request.t0Ms.toInt();
      if (call == 3) {
        // One sample with a much higher round-trip delay and a very different
        // (untrustworthy) offset - this is the outlier reject_outliers should drop.
        clock += 400;
        return ClockSyncReply(t0Ms: Int64(t0), t1Ms: Int64(t0 + 300), t2Ms: Int64(t0 + 305));
      }
      clock += 4;
      return ClockSyncReply(t0Ms: Int64(t0), t1Ms: Int64(t0 + 21), t2Ms: Int64(t0 + 23));
    }

    final sampler = ClockSyncSampler(exchange, nowMs: () => clock);
    final estimate = await sampler.sampleBurst(count: 5, spacing: Duration.zero);

    // If the outlier (offset ~102.5) had been kept, the average would land near 36.5,
    // not close to the 4 consistent normal samples' offset of 20.
    expect(estimate.offsetMs, closeTo(20, 2));
  });

  test('serverTimeToLocalMs applies the offset', () async {
    final clock = 1000000;

    Future<ClockSyncReply> exchange(ClockSyncRequest request) async {
      final t0 = request.t0Ms.toInt();
      return ClockSyncReply(t0Ms: Int64(t0), t1Ms: Int64(t0 + 30), t2Ms: Int64(t0 + 30));
    }

    final sampler = ClockSyncSampler(exchange, nowMs: () => clock);
    await sampler.sampleBurst(count: 1, spacing: Duration.zero);

    // offset ~= +30 (server ahead of node), so local time = serverMs - offset.
    final local = sampler.serverTimeToLocalMs(1000030);
    expect(local, closeTo(1000000, 1));
  });
}
