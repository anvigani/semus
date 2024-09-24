
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 110 mm) (* 35 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' { 
\omit Staff.TimeSignature 
%\hide Staff.Stem
\hide Staff.BarLine

\override Score.MetronomeMark.padding = 3
                             \tempo 1 = 60        % Tempi
\time 4/4
c1 4 4 4 4 2 2 8 8 8 8 8 8 8 8  2 2 1 
}