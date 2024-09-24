
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 75 mm) (* 20 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\layout{#(layout-set-staff-size 20) indent = 5 short-indent = 5 } 
\header {tagline = ""}


\new Staff \with{
                \remove "Bar_engraver"
                \remove "Time_signature_engraver"  
                \remove "Clef_engraver"
                \override StaffSymbol.line-count = #1                              
                }
\relative c' { \clef percussion
                         \set Score.barNumberVisibility = ##f
                   c16 c c8 c2 c4
              }