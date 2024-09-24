
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 92 mm) (* 40 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}


\new Staff \with{
                \remove "Bar_engraver"
                \remove "Time_signature_engraver"  
                \override StaffSymbol.line-count = #1                              
                }
\relative c' { 
              \clef  percussion 
              \override Score.MetronomeMark.padding = 8
              \tempo  4 = 60      
                   
              c2^"|"-\tweak self-alignment-X #-0.25 ^"0000" r
              c4^"|"-\tweak self-alignment-X #-0.25 ^"4000" r
              c4^"|"-\tweak self-alignment-X #-0.25 ^"6000" r
              c4^"|"-\tweak self-alignment-X #-0.25 ^"8000" r8
              c8^"|"-\tweak self-alignment-X #-0.25 ^"9500" r4
              c4^"|"-\tweak self-alignment-X #-0.25 ^"11000" 
              }