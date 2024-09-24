
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 92 mm) (* 25 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' { 
\omit Staff.TimeSignature 
\hide Staff.Stem
\hide Staff.Clef
\hide Staff.BarLine
  
s1 s  s^"pentagramma"s s s s 
}