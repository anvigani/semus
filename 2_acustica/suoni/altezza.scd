s.waitForBoot {
    SynthDef(\sine, {arg freq=400, amp=1, dur=1;
                     var sig, env;
                         sig = SinOsc.ar(freq);
                         env = Env.perc(0.01, dur-0.01).ar(Done.freeSelf);
                         sig = Pan2.ar(sig * env * amp, 0);
                     Out.ar(0, sig);
    }).add;
    s.sync;
	s.prepareForRecord("/Users/andreavigani/Desktop/musicaecodice/anew/semiotica/2_acustica/suoni/audio.wav");
    s.sync;
	~gradi = (80 + [22,0,17,13]).midicps;
	~delta = [1,1];
    s.record;
    Routine.new({
                 ~gradi.do({arg i,id;
                            Synth(\sine, [\freq, i,\dur,1,\amp, 0.15]);
			                ~delta.wrapAt(id).wait;
                            });
                 4.wait;
                 s.stopRecording;
                 }).play;
};