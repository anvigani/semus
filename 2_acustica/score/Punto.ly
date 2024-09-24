
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 120 mm) (* 25 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' {
  
\omit Staff.TimeSignature 
%\hide Staff.Stem
\hide Staff.BarLine
  \time 4/4
c8. e16 d4. f8 e8.. g32 f32 g a b  c4. g2
}