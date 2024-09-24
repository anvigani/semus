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
	~amp = [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0];
	~delta = [0.5,0.5];
    s.record;
    Routine.new({
                 30.do({arg i,id;
			Synth(\sine, [\freq, 92.midicps,\dur,0.5,\amp, ~amp.choose**4]);
			                0.2.wait;
                            });
                 1.wait;
                 s.stopRecording;
                 }).play;
};