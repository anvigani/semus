
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 120 mm) (* 35 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' { 
\omit Staff.TimeSignature 
%\hide Staff.Stem
\hide Staff.BarLine

\override Score.MetronomeMark.padding = 3
                             \tempo 4 = 60        % Tempi
                             
\time 5/4

c4 r4 e8 g8 r8 c4. r4 e2.

}