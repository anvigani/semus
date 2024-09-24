
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 140 mm) (* 40 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}


\new Staff \with{
                \remove "Bar_engraver"
                \remove "Time_signature_engraver"  
                \override StaffSymbol.line-count = #1                              
                }
\relative c' {
                \clef  percussion
                \override Score.MetronomeMark.padding = 6
                \tempo  4 = 60      
                \set Score.proportionalNotationDuration = #(ly:make-moment 1/16)
                   
                \slurDashed  c16_"__"_"250"        -\tweak self-alignment-X #-1.9 ^"1000" (r8. 
                              c16_"__"_"250" ) (r8. -\tweak self-alignment-X #-1.1 ^"1000" 
                              c16_"__"_"250" ) (r8. -\tweak self-alignment-X #-1.0 ^"1000" 
                              c16_"__"_"250" ) (r8. -\tweak self-alignment-X #-1.0 ^"1000"  
                              c8_"____"_"500" )      -\tweak self-alignment-X #-1.9 ^"1000" (r8 
                              c8_"____"_"500") (r8   -\tweak self-alignment-X #-0.3 ^"1000" 
                              c8_"____"_"500") (r8   -\tweak self-alignment-X #-0.35 ^"1000" 
                              c8_"____"_"500") r8 s16 
                    }