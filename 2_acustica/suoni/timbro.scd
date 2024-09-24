s.waitForBoot {
    SynthDef(\sine, {arg freq=400, amp=1, dur=1;
                     var sig, env;
                         sig = SinOsc.ar(freq);
                         env = Env.perc(0.01, dur-0.01).ar(Done.freeSelf);
                         sig = Pan2.ar(sig * env * amp, 0);
                     Out.ar(0, sig);
    }).add;
    s.sync;
	s.prepareForRecord("audio.wav".resolveRelative);
    s.sync;
	~freqs = 300 * [1,2,3,4,5,6,7,8,9,10];
	~delta = [0.5,0.5];
    s.record;
    Routine.new({
                 ~freqs.do({arg i,id;
			Synth(\sine, [\freq, i,\dur,rrand(0.1,15),\amp, 0.01]);
                            });
                 15.wait;
                 s.stopRecording;
                 }).play;
};