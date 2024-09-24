
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 75 mm) (* 60 mm))) paper-alist))     
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
                   
                c1\pppp c\ppp c\pp  c\p    c\mp    \break
                c\mf    c\f   c\ff  c\ffff c\ffff  \break
                c\fp    c\sf  c\sff c\sfz  c\rfz  
              }