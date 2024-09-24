
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
               \override Score.MetronomeMark.padding = 6
               \tempo  4 = 60      
                   
               \slurDashed   c -\tweak self-alignment-X #-1.75 ^"1000" 
                           (s c -\tweak self-alignment-X #-1.75 ^"1000") 
                           (s c -\tweak self-alignment-X #-1.75 ^"1000") 
                           (s c)
               }