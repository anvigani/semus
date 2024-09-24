
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
                             \tempo 4 = 60        % Tempi
\time 4/4
c4 16 16 16 16 8 8 32 32 32 32 32 32 32 32  8 8 4 
}